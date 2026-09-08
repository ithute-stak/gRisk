import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select

from app.api.deps import CurrentUser, DbSession
from app.models.partner import Partner
from app.schemas.partner import PartnerCreate, PartnerListResponse, PartnerResponse, PartnerUpdate
from app.services.audit import record_audit_event

router = APIRouter(prefix="/partners", tags=["partners"])
Page = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]
Search = Annotated[str | None, Query(max_length=200)]


async def _partner_or_404(session: DbSession, partner_id: uuid.UUID) -> Partner:
    partner = await session.get(Partner, partner_id)
    if partner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")
    return partner


def _partner_number() -> str:
    return f"PAR-{uuid.uuid4().hex[:10].upper()}"


@router.get("", response_model=PartnerListResponse)
async def list_partners(
    _: CurrentUser,
    session: DbSession,
    page: Page = 1,
    page_size: PageSize = 25,
    q: Search = None,
    partner_type: str | None = Query(default=None, max_length=50),
    integration_status: str | None = Query(default=None, max_length=40),
    active: bool | None = None,
) -> PartnerListResponse:
    filters = []
    if q:
        term = f"%{q.strip()}%"
        filters.append(
            or_(
                Partner.name.ilike(term),
                Partner.partner_number.ilike(term),
                Partner.email.ilike(term),
                Partner.external_reference.ilike(term),
            )
        )
    if partner_type:
        filters.append(Partner.partner_type == partner_type)
    if integration_status:
        filters.append(Partner.integration_status == integration_status)
    if active is not None:
        filters.append(Partner.is_active.is_(active))

    total = await session.scalar(select(func.count(Partner.id)).where(*filters)) or 0
    result = await session.execute(
        select(Partner)
        .where(*filters)
        .order_by(Partner.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return PartnerListResponse(
        items=list(result.scalars().all()),
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=PartnerResponse, status_code=status.HTTP_201_CREATED)
async def create_partner(
    payload: PartnerCreate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
) -> PartnerResponse:
    existing = await session.scalar(
        select(Partner.id).where(func.lower(Partner.name) == payload.name.strip().lower())
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Partner name already exists")

    partner = Partner(
        partner_number=_partner_number(),
        partner_type=payload.partner_type,
        name=payload.name.strip(),
        email=str(payload.email).lower() if payload.email else None,
        phone=payload.phone.strip() if payload.phone else None,
        website=payload.website.strip() if payload.website else None,
        external_reference=payload.external_reference.strip() if payload.external_reference else None,
        integration_status=payload.integration_status,
        notes=payload.notes.strip() if payload.notes else None,
        is_active=payload.is_active,
    )
    session.add(partner)
    await session.flush()
    await record_audit_event(
        session,
        action="partner.created",
        entity_type="partner",
        entity_id=str(partner.id),
        actor_user_id=user.id,
        details={
            "partner_number": partner.partner_number,
            "partner_type": partner.partner_type,
            "name": partner.name,
        },
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    await session.refresh(partner)
    return partner


@router.patch("/{partner_id}", response_model=PartnerResponse)
async def update_partner(
    partner_id: uuid.UUID,
    payload: PartnerUpdate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
) -> PartnerResponse:
    partner = await _partner_or_404(session, partner_id)
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"] is not None:
        normalized_name = changes["name"].strip()
        duplicate = await session.scalar(
            select(Partner.id).where(
                func.lower(Partner.name) == normalized_name.lower(),
                Partner.id != partner.id,
            )
        )
        if duplicate is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Partner name already exists")
        changes["name"] = normalized_name
    if "email" in changes and changes["email"] is not None:
        changes["email"] = str(changes["email"]).lower()
    for field in ("phone", "website", "external_reference", "notes"):
        if field in changes and changes[field] is not None:
            changes[field] = changes[field].strip()
    for field, value in changes.items():
        setattr(partner, field, value)

    await record_audit_event(
        session,
        action="partner.updated",
        entity_type="partner",
        entity_id=str(partner.id),
        actor_user_id=user.id,
        details={"changed_fields": sorted(payload.model_fields_set)},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    await session.refresh(partner)
    return partner
