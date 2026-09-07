import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models.claim import Claim, ClaimEvent
from app.models.insurance import Policy
from app.realtime.manager import manager
from app.schemas.claim import (
    ClaimCreate,
    ClaimEventResponse,
    ClaimListResponse,
    ClaimNoteCreate,
    ClaimResponse,
    ClaimStatusUpdate,
)
from app.services.audit import record_audit_event

router = APIRouter(prefix="/claims", tags=["claims"])
Page = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]
Search = Annotated[str | None, Query(max_length=200)]

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "reported": {"triage", "documents_pending", "rejected"},
    "triage": {"documents_pending", "assessment", "rejected"},
    "documents_pending": {"triage", "assessment", "rejected"},
    "assessment": {"insurer_review", "approved", "rejected"},
    "insurer_review": {"documents_pending", "approved", "rejected"},
    "approved": {"settled"},
    "rejected": {"closed"},
    "settled": {"closed"},
    "closed": set(),
}


def _claim_options():
    return (selectinload(Claim.events),)


async def _get_claim_or_404(session: DbSession, claim_id: uuid.UUID) -> Claim:
    result = await session.execute(
        select(Claim).options(*_claim_options()).where(Claim.id == claim_id)
    )
    claim = result.scalar_one_or_none()
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    return claim


@router.get("", response_model=ClaimListResponse)
async def list_claims(
    _: CurrentUser,
    session: DbSession,
    page: Page = 1,
    page_size: PageSize = 25,
    q: Search = None,
    claim_status: str | None = Query(default=None, max_length=30),
    priority: str | None = Query(default=None, max_length=20),
    customer_id: uuid.UUID | None = None,
    policy_id: uuid.UUID | None = None,
) -> ClaimListResponse:
    filters = []
    if q:
        term = f"%{q.strip()}%"
        filters.append(or_(Claim.claim_number.ilike(term), Claim.description.ilike(term)))
    if claim_status:
        filters.append(Claim.status == claim_status)
    if priority:
        filters.append(Claim.priority == priority)
    if customer_id:
        filters.append(Claim.customer_id == customer_id)
    if policy_id:
        filters.append(Claim.policy_id == policy_id)

    total = await session.scalar(select(func.count(Claim.id)).where(*filters))
    result = await session.execute(
        select(Claim)
        .where(*filters)
        .order_by(Claim.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return ClaimListResponse(
        items=list(result.scalars().all()),
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=ClaimResponse, status_code=status.HTTP_201_CREATED)
async def create_claim(
    payload: ClaimCreate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
) -> Claim:
    policy = await session.get(Policy, payload.policy_id)
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    if payload.incident_date < policy.start_date or payload.incident_date > policy.end_date:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Incident date is outside the policy cover period",
        )

    claim = Claim(
        policy_id=policy.id,
        customer_id=policy.customer_id,
        claim_type=payload.claim_type.strip(),
        incident_date=payload.incident_date,
        description=payload.description.strip(),
        claim_amount=payload.claim_amount,
        priority=payload.priority,
        created_by_user_id=user.id,
    )
    session.add(claim)
    await session.flush()

    session.add(
        ClaimEvent(
            claim_id=claim.id,
            event_type="claim.reported",
            note="Claim registered in gRisk.",
            to_status="reported",
            actor_user_id=user.id,
        )
    )
    await record_audit_event(
        session,
        action="claim.created",
        entity_type="claim",
        entity_id=str(claim.id),
        actor_user_id=user.id,
        details={
            "claim_number": claim.claim_number,
            "policy_id": str(policy.id),
            "claim_amount": str(claim.claim_amount),
        },
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()

    created = await _get_claim_or_404(session, claim.id)
    await manager.broadcast(
        "claims",
        {
            "channel": "claims",
            "event": "claim.created",
            "data": {"id": str(created.id), "claim_number": created.claim_number},
        },
    )
    return created


@router.get("/{claim_id}", response_model=ClaimResponse)
async def get_claim(claim_id: uuid.UUID, _: CurrentUser, session: DbSession) -> Claim:
    return await _get_claim_or_404(session, claim_id)


@router.patch("/{claim_id}/status", response_model=ClaimResponse)
async def update_claim_status(
    claim_id: uuid.UUID,
    payload: ClaimStatusUpdate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
) -> Claim:
    claim = await _get_claim_or_404(session, claim_id)
    previous_status = claim.status

    if payload.status == previous_status:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Claim is already in the requested status",
        )

    allowed = ALLOWED_TRANSITIONS.get(previous_status, set())
    if payload.status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid claim transition: {previous_status} -> {payload.status}",
        )

    if payload.status == "approved":
        if payload.approved_amount is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="approved_amount is required when approving a claim",
            )
        if payload.approved_amount > claim.claim_amount:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="approved_amount cannot exceed claim_amount",
            )
        claim.approved_amount = payload.approved_amount

    claim.status = payload.status
    event = ClaimEvent(
        claim_id=claim.id,
        event_type="claim.status_changed",
        note=payload.note,
        from_status=previous_status,
        to_status=payload.status,
        actor_user_id=user.id,
    )
    session.add(event)
    await record_audit_event(
        session,
        action="claim.status_changed",
        entity_type="claim",
        entity_id=str(claim.id),
        actor_user_id=user.id,
        details={
            "from": previous_status,
            "to": payload.status,
            "approved_amount": str(claim.approved_amount) if claim.approved_amount is not None else None,
        },
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()

    updated = await _get_claim_or_404(session, claim.id)
    await manager.broadcast(
        "claims",
        {
            "channel": "claims",
            "event": "claim.status_changed",
            "data": {"id": str(updated.id), "status": updated.status},
        },
    )
    return updated


@router.post(
    "/{claim_id}/notes",
    response_model=ClaimEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_claim_note(
    claim_id: uuid.UUID,
    payload: ClaimNoteCreate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
) -> ClaimEvent:
    claim = await _get_claim_or_404(session, claim_id)
    event = ClaimEvent(
        claim_id=claim.id,
        event_type="claim.note_added",
        note=payload.note.strip(),
        actor_user_id=user.id,
    )
    session.add(event)
    await session.flush()
    await record_audit_event(
        session,
        action="claim.note_added",
        entity_type="claim",
        entity_id=str(claim.id),
        actor_user_id=user.id,
        details={"event_id": str(event.id)},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    await session.refresh(event)
    return event
