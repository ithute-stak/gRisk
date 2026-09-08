import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models.customer import Customer
from app.models.guarantee import Guarantee, GuaranteeEvent
from app.realtime.manager import manager
from app.schemas.guarantee import (
    GuaranteeCreate,
    GuaranteeListResponse,
    GuaranteeResponse,
    GuaranteeStatusUpdate,
    GuaranteeUpdate,
)
from app.services.audit import record_audit_event

router = APIRouter(prefix="/guarantees", tags=["bonds-guarantees"])
Page = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]
Search = Annotated[str | None, Query(max_length=200)]

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"review", "cancelled"},
    "review": {"draft", "submitted", "declined", "cancelled"},
    "submitted": {"review", "approved", "declined", "cancelled"},
    "approved": {"issued", "cancelled"},
    "declined": {"closed"},
    "issued": {"released", "expired", "cancelled"},
    "released": {"closed"},
    "expired": {"closed"},
    "cancelled": {"closed"},
    "closed": set(),
}


def _guarantee_options():
    return (selectinload(Guarantee.events),)


async def _get_guarantee_or_404(session: DbSession, guarantee_id: uuid.UUID) -> Guarantee:
    result = await session.execute(
        select(Guarantee).options(*_guarantee_options()).where(Guarantee.id == guarantee_id)
    )
    guarantee = result.scalar_one_or_none()
    if guarantee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guarantee not found")
    return guarantee


def _validate_amounts(guarantee_amount, contract_value) -> None:
    if contract_value is not None and guarantee_amount > contract_value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="guarantee_amount cannot exceed contract_value",
        )


@router.get("", response_model=GuaranteeListResponse)
async def list_guarantees(
    _: CurrentUser,
    session: DbSession,
    page: Page = 1,
    page_size: PageSize = 25,
    q: Search = None,
    guarantee_status: str | None = Query(default=None, max_length=30),
    guarantee_type: str | None = Query(default=None, max_length=60),
    customer_id: uuid.UUID | None = None,
):
    filters = []
    if q:
        term = f"%{q.strip()}%"
        filters.append(
            or_(
                Guarantee.guarantee_number.ilike(term),
                Guarantee.beneficiary.ilike(term),
                Guarantee.tender_reference.ilike(term),
                Guarantee.contract_reference.ilike(term),
                Guarantee.issuer_name.ilike(term),
            )
        )
    if guarantee_status:
        filters.append(Guarantee.status == guarantee_status)
    if guarantee_type:
        filters.append(Guarantee.guarantee_type == guarantee_type)
    if customer_id:
        filters.append(Guarantee.customer_id == customer_id)

    total = await session.scalar(select(func.count(Guarantee.id)).where(*filters))
    result = await session.execute(
        select(Guarantee)
        .where(*filters)
        .order_by(Guarantee.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return GuaranteeListResponse(
        items=list(result.scalars().all()),
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=GuaranteeResponse, status_code=status.HTTP_201_CREATED)
async def create_guarantee(
    payload: GuaranteeCreate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
):
    customer = await session.get(Customer, payload.customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    guarantee = Guarantee(
        **payload.model_dump(exclude={"currency"}),
        currency=payload.currency.upper(),
        created_by_user_id=user.id,
    )
    session.add(guarantee)
    await session.flush()
    session.add(
        GuaranteeEvent(
            guarantee_id=guarantee.id,
            event_type="guarantee.created",
            note="Guarantee application created in gRisk.",
            to_status="draft",
            actor_user_id=user.id,
        )
    )
    await record_audit_event(
        session,
        action="guarantee.created",
        entity_type="guarantee",
        entity_id=str(guarantee.id),
        actor_user_id=user.id,
        details={
            "guarantee_number": guarantee.guarantee_number,
            "guarantee_type": guarantee.guarantee_type,
            "customer_id": str(customer.id),
            "amount": str(guarantee.guarantee_amount),
        },
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    created = await _get_guarantee_or_404(session, guarantee.id)
    await manager.broadcast(
        "guarantees",
        {
            "channel": "guarantees",
            "event": "guarantee.created",
            "data": {"id": str(created.id), "guarantee_number": created.guarantee_number},
        },
    )
    return created


@router.get("/{guarantee_id}", response_model=GuaranteeResponse)
async def get_guarantee(guarantee_id: uuid.UUID, _: CurrentUser, session: DbSession):
    return await _get_guarantee_or_404(session, guarantee_id)


@router.patch("/{guarantee_id}", response_model=GuaranteeResponse)
async def update_guarantee(
    guarantee_id: uuid.UUID,
    payload: GuaranteeUpdate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
):
    guarantee = await _get_guarantee_or_404(session, guarantee_id)
    if guarantee.status not in {"draft", "review", "submitted", "approved"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Issued or closed guarantees cannot be edited",
        )
    changes = payload.model_dump(exclude_unset=True)
    guarantee_amount = changes.get("guarantee_amount", guarantee.guarantee_amount)
    contract_value = changes.get("contract_value", guarantee.contract_value)
    _validate_amounts(guarantee_amount, contract_value)
    effective_date = changes.get("effective_date", guarantee.effective_date)
    expiry_date = changes.get("expiry_date", guarantee.expiry_date)
    if effective_date and expiry_date and expiry_date < effective_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="expiry_date must be on or after effective_date",
        )
    for field, value in changes.items():
        setattr(guarantee, field, value)
    await record_audit_event(
        session,
        action="guarantee.updated",
        entity_type="guarantee",
        entity_id=str(guarantee.id),
        actor_user_id=user.id,
        details={"changed_fields": sorted(changes)},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    return await _get_guarantee_or_404(session, guarantee.id)


@router.patch("/{guarantee_id}/status", response_model=GuaranteeResponse)
async def update_guarantee_status(
    guarantee_id: uuid.UUID,
    payload: GuaranteeStatusUpdate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
):
    guarantee = await _get_guarantee_or_404(session, guarantee_id)
    previous = guarantee.status
    if payload.status not in ALLOWED_TRANSITIONS.get(previous, set()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid guarantee transition: {previous} -> {payload.status}",
        )
    if payload.status == "issued":
        if not guarantee.issuer_name:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="issuer_name is required before a guarantee can be issued",
            )
        if not guarantee.effective_date or not guarantee.expiry_date:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="effective_date and expiry_date are required before issuance",
            )

    guarantee.status = payload.status
    session.add(
        GuaranteeEvent(
            guarantee_id=guarantee.id,
            event_type="guarantee.status_changed",
            note=payload.note,
            from_status=previous,
            to_status=payload.status,
            actor_user_id=user.id,
        )
    )
    await record_audit_event(
        session,
        action="guarantee.status_changed",
        entity_type="guarantee",
        entity_id=str(guarantee.id),
        actor_user_id=user.id,
        details={"from": previous, "to": payload.status},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    updated = await _get_guarantee_or_404(session, guarantee.id)
    await manager.broadcast(
        "guarantees",
        {
            "channel": "guarantees",
            "event": "guarantee.status_changed",
            "data": {"id": str(updated.id), "status": updated.status},
        },
    )
    return updated
