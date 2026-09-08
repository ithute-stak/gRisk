import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models.customer import Customer
from app.models.medical import (
    MedicalAuthorisation,
    MedicalBenefit,
    MedicalClaim,
    MedicalDependant,
    MedicalMember,
    MedicalPlan,
    MedicalUtilisation,
)
from app.realtime.manager import manager
from app.schemas.medical import (
    BenefitBalanceResponse,
    MedicalAuthorisationCreate,
    MedicalAuthorisationDecision,
    MedicalAuthorisationResponse,
    MedicalBenefitCreate,
    MedicalBenefitResponse,
    MedicalClaimCreate,
    MedicalClaimResponse,
    MedicalClaimStatusUpdate,
    MedicalDependantCreate,
    MedicalDependantResponse,
    MedicalMemberCreate,
    MedicalMemberListResponse,
    MedicalMemberResponse,
    MedicalMemberUpdate,
    MedicalPlanCreate,
    MedicalPlanResponse,
    MedicalUtilisationCreate,
    MedicalUtilisationResponse,
)
from app.services.audit import record_audit_event

router = APIRouter(prefix="/medical", tags=["medical-aid"])
Page = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]
Search = Annotated[str | None, Query(max_length=200)]


async def _plan_or_404(session: DbSession, plan_id: uuid.UUID) -> MedicalPlan:
    result = await session.execute(
        select(MedicalPlan).options(selectinload(MedicalPlan.benefits)).where(MedicalPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medical plan not found")
    return plan


async def _member_or_404(session: DbSession, member_id: uuid.UUID) -> MedicalMember:
    result = await session.execute(
        select(MedicalMember)
        .options(selectinload(MedicalMember.dependants))
        .where(MedicalMember.id == member_id)
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medical member not found")
    return member


async def _benefit_or_404(session: DbSession, benefit_id: uuid.UUID) -> MedicalBenefit:
    benefit = await session.get(MedicalBenefit, benefit_id)
    if benefit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medical benefit not found")
    return benefit


async def _validate_dependant(session: DbSession, member_id: uuid.UUID, dependant_id: uuid.UUID | None) -> None:
    if dependant_id is None:
        return
    dependant = await session.get(MedicalDependant, dependant_id)
    if dependant is None or dependant.member_id != member_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Dependant does not belong to member")


@router.get("/plans", response_model=list[MedicalPlanResponse])
async def list_plans(_: CurrentUser, session: DbSession, active_only: bool = True):
    query = select(MedicalPlan).options(selectinload(MedicalPlan.benefits)).order_by(MedicalPlan.name)
    if active_only:
        query = query.where(MedicalPlan.is_active.is_(True))
    result = await session.execute(query)
    return list(result.scalars().unique().all())


@router.post("/plans", response_model=MedicalPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(payload: MedicalPlanCreate, request: Request, user: CurrentUser, session: DbSession):
    existing = await session.scalar(select(MedicalPlan).where(MedicalPlan.code == payload.code.upper()))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Medical plan code already exists")
    plan = MedicalPlan(**payload.model_dump(exclude={"code", "currency"}), code=payload.code.upper(), currency=payload.currency.upper())
    session.add(plan)
    await session.flush()
    await record_audit_event(
        session,
        action="medical.plan_created",
        entity_type="medical_plan",
        entity_id=str(plan.id),
        actor_user_id=user.id,
        details={"code": plan.code, "name": plan.name},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    return await _plan_or_404(session, plan.id)


@router.post(
    "/plans/{plan_id}/benefits",
    response_model=MedicalBenefitResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_benefit(
    plan_id: uuid.UUID,
    payload: MedicalBenefitCreate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
):
    await _plan_or_404(session, plan_id)
    code = payload.code.upper()
    existing = await session.scalar(
        select(MedicalBenefit).where(MedicalBenefit.plan_id == plan_id, MedicalBenefit.code == code)
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Benefit code already exists on plan")
    benefit = MedicalBenefit(plan_id=plan_id, **payload.model_dump(exclude={"code"}), code=code)
    session.add(benefit)
    await session.flush()
    await record_audit_event(
        session,
        action="medical.benefit_created",
        entity_type="medical_benefit",
        entity_id=str(benefit.id),
        actor_user_id=user.id,
        details={"plan_id": str(plan_id), "code": benefit.code},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    await session.refresh(benefit)
    return benefit


@router.get("/members", response_model=MedicalMemberListResponse)
async def list_members(
    _: CurrentUser,
    session: DbSession,
    page: Page = 1,
    page_size: PageSize = 25,
    q: Search = None,
    member_status: str | None = Query(default=None, max_length=30),
    plan_id: uuid.UUID | None = None,
):
    filters = []
    if q:
        term = f"%{q.strip()}%"
        filters.append(MedicalMember.member_number.ilike(term))
    if member_status:
        filters.append(MedicalMember.status == member_status)
    if plan_id:
        filters.append(MedicalMember.plan_id == plan_id)
    total = await session.scalar(select(func.count(MedicalMember.id)).where(*filters))
    result = await session.execute(
        select(MedicalMember)
        .where(*filters)
        .order_by(MedicalMember.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return MedicalMemberListResponse(
        items=list(result.scalars().all()), total=total or 0, page=page, page_size=page_size
    )


@router.post("/members", response_model=MedicalMemberResponse, status_code=status.HTTP_201_CREATED)
async def create_member(
    payload: MedicalMemberCreate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
):
    if await session.get(Customer, payload.customer_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    plan = await _plan_or_404(session, payload.plan_id)
    if not plan.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Medical plan is inactive")
    existing = await session.scalar(
        select(MedicalMember).where(
            MedicalMember.customer_id == payload.customer_id,
            MedicalMember.status.in_(["active", "suspended"]),
        )
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Customer already has an active medical membership")
    member = MedicalMember(**payload.model_dump(), created_by_user_id=user.id)
    session.add(member)
    await session.flush()
    await record_audit_event(
        session,
        action="medical.member_created",
        entity_type="medical_member",
        entity_id=str(member.id),
        actor_user_id=user.id,
        details={"member_number": member.member_number, "plan_id": str(plan.id)},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    created = await _member_or_404(session, member.id)
    await manager.broadcast(
        "medical",
        {"channel": "medical", "event": "medical.member_created", "data": {"id": str(created.id), "member_number": created.member_number}},
    )
    return created


@router.get("/members/{member_id}", response_model=MedicalMemberResponse)
async def get_member(member_id: uuid.UUID, _: CurrentUser, session: DbSession):
    return await _member_or_404(session, member_id)


@router.patch("/members/{member_id}", response_model=MedicalMemberResponse)
async def update_member(
    member_id: uuid.UUID,
    payload: MedicalMemberUpdate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
):
    member = await _member_or_404(session, member_id)
    changes = payload.model_dump(exclude_unset=True)
    if "plan_id" in changes and changes["plan_id"] is not None:
        await _plan_or_404(session, changes["plan_id"])
    start_date = changes.get("start_date", member.start_date)
    end_date = changes.get("end_date", member.end_date)
    if end_date and end_date < start_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="end_date must be on or after start_date")
    for field, value in changes.items():
        setattr(member, field, value)
    await record_audit_event(
        session,
        action="medical.member_updated",
        entity_type="medical_member",
        entity_id=str(member.id),
        actor_user_id=user.id,
        details={"changed_fields": sorted(changes)},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    return await _member_or_404(session, member.id)


@router.post(
    "/members/{member_id}/dependants",
    response_model=MedicalDependantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_dependant(
    member_id: uuid.UUID,
    payload: MedicalDependantCreate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
):
    await _member_or_404(session, member_id)
    dependant = MedicalDependant(member_id=member_id, **payload.model_dump())
    session.add(dependant)
    await session.flush()
    await record_audit_event(
        session,
        action="medical.dependant_created",
        entity_type="medical_dependant",
        entity_id=str(dependant.id),
        actor_user_id=user.id,
        details={"member_id": str(member_id), "relationship": dependant.relationship_type},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    await session.refresh(dependant)
    return dependant


async def _benefit_balance(session: DbSession, member: MedicalMember, benefit: MedicalBenefit, year: int) -> BenefitBalanceResponse:
    totals = await session.execute(
        select(
            func.coalesce(func.sum(MedicalUtilisation.amount), 0),
            func.coalesce(func.sum(MedicalUtilisation.units), 0),
        ).where(
            MedicalUtilisation.member_id == member.id,
            MedicalUtilisation.benefit_id == benefit.id,
            func.extract("year", MedicalUtilisation.service_date) == year,
        )
    )
    used_amount_raw, used_units_raw = totals.one()
    used_amount = Decimal(used_amount_raw)
    used_units = int(used_units_raw)
    remaining_amount = None
    if benefit.annual_monetary_limit is not None:
        remaining_amount = max(Decimal(0), benefit.annual_monetary_limit - used_amount)
    remaining_units = None
    if benefit.annual_visit_limit is not None:
        remaining_units = max(0, benefit.annual_visit_limit - used_units)
    return BenefitBalanceResponse(
        member_id=member.id,
        benefit_id=benefit.id,
        benefit_code=benefit.code,
        benefit_name=benefit.name,
        year=year,
        used_amount=used_amount,
        remaining_amount=remaining_amount,
        used_units=used_units,
        remaining_units=remaining_units,
    )


@router.get("/members/{member_id}/benefits/{benefit_id}/balance", response_model=BenefitBalanceResponse)
async def get_benefit_balance(
    member_id: uuid.UUID,
    benefit_id: uuid.UUID,
    _: CurrentUser,
    session: DbSession,
    year: int = Query(ge=2000, le=2200),
):
    member = await _member_or_404(session, member_id)
    benefit = await _benefit_or_404(session, benefit_id)
    if benefit.plan_id != member.plan_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Benefit is not part of member plan")
    return await _benefit_balance(session, member, benefit, year)


@router.post("/utilisations", response_model=MedicalUtilisationResponse, status_code=status.HTTP_201_CREATED)
async def record_utilisation(
    payload: MedicalUtilisationCreate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
):
    member = await _member_or_404(session, payload.member_id)
    benefit = await _benefit_or_404(session, payload.benefit_id)
    if member.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Medical membership is not active")
    if benefit.plan_id != member.plan_id or not benefit.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Benefit is not active on member plan")
    if payload.service_date < member.start_date or (member.end_date and payload.service_date > member.end_date):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Service date is outside membership period")
    await _validate_dependant(session, member.id, payload.dependant_id)
    if benefit.requires_authorisation:
        approved = await session.scalar(
            select(MedicalAuthorisation).where(
                MedicalAuthorisation.member_id == member.id,
                MedicalAuthorisation.benefit_id == benefit.id,
                MedicalAuthorisation.status == "approved",
            )
        )
        if approved is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Benefit requires an approved authorisation")
    if benefit.per_event_limit is not None and payload.amount > benefit.per_event_limit:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Amount exceeds benefit per-event limit")
    balance = await _benefit_balance(session, member, benefit, payload.service_date.year)
    if balance.remaining_amount is not None and payload.amount > balance.remaining_amount:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Amount exceeds remaining annual benefit")
    if balance.remaining_units is not None and payload.units > balance.remaining_units:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Units exceed remaining annual visit limit")
    utilisation = MedicalUtilisation(**payload.model_dump(), created_by_user_id=user.id)
    session.add(utilisation)
    await session.flush()
    await record_audit_event(
        session,
        action="medical.utilisation_recorded",
        entity_type="medical_utilisation",
        entity_id=str(utilisation.id),
        actor_user_id=user.id,
        details={"member_id": str(member.id), "benefit_code": benefit.code, "amount": str(utilisation.amount)},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    await session.refresh(utilisation)
    await manager.broadcast(
        "medical",
        {"channel": "medical", "event": "medical.utilisation_recorded", "data": {"member_id": str(member.id), "benefit_id": str(benefit.id)}},
    )
    return utilisation


@router.post("/authorisations", response_model=MedicalAuthorisationResponse, status_code=status.HTTP_201_CREATED)
async def request_authorisation(
    payload: MedicalAuthorisationCreate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
):
    member = await _member_or_404(session, payload.member_id)
    benefit = await _benefit_or_404(session, payload.benefit_id)
    if benefit.plan_id != member.plan_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Benefit is not part of member plan")
    await _validate_dependant(session, member.id, payload.dependant_id)
    authorisation = MedicalAuthorisation(**payload.model_dump(), created_by_user_id=user.id)
    session.add(authorisation)
    await session.flush()
    await record_audit_event(
        session,
        action="medical.authorisation_requested",
        entity_type="medical_authorisation",
        entity_id=str(authorisation.id),
        actor_user_id=user.id,
        details={"member_id": str(member.id), "benefit_id": str(benefit.id)},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    await session.refresh(authorisation)
    return authorisation


@router.patch("/authorisations/{authorisation_id}", response_model=MedicalAuthorisationResponse)
async def decide_authorisation(
    authorisation_id: uuid.UUID,
    payload: MedicalAuthorisationDecision,
    request: Request,
    user: CurrentUser,
    session: DbSession,
):
    authorisation = await session.get(MedicalAuthorisation, authorisation_id)
    if authorisation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medical authorisation not found")
    if authorisation.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Authorisation has already been decided")
    if payload.status == "approved" and payload.approved_amount is not None and authorisation.requested_amount is not None and payload.approved_amount > authorisation.requested_amount:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="approved_amount cannot exceed requested_amount")
    authorisation.status = payload.status
    authorisation.approved_amount = payload.approved_amount
    if payload.notes is not None:
        authorisation.notes = payload.notes
    authorisation.decided_at = datetime.now(UTC)
    await record_audit_event(
        session,
        action="medical.authorisation_decided",
        entity_type="medical_authorisation",
        entity_id=str(authorisation.id),
        actor_user_id=user.id,
        details={"status": payload.status, "approved_amount": str(payload.approved_amount) if payload.approved_amount is not None else None},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    await session.refresh(authorisation)
    return authorisation


@router.post("/claims", response_model=MedicalClaimResponse, status_code=status.HTTP_201_CREATED)
async def create_medical_claim(
    payload: MedicalClaimCreate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
):
    member = await _member_or_404(session, payload.member_id)
    await _validate_dependant(session, member.id, payload.dependant_id)
    if payload.service_date < member.start_date or (member.end_date and payload.service_date > member.end_date):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Service date is outside membership period")
    claim = MedicalClaim(**payload.model_dump(), created_by_user_id=user.id)
    session.add(claim)
    await session.flush()
    await record_audit_event(
        session,
        action="medical.claim_created",
        entity_type="medical_claim",
        entity_id=str(claim.id),
        actor_user_id=user.id,
        details={"claim_number": claim.claim_number, "claim_kind": claim.claim_kind, "amount": str(claim.claim_amount)},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    await session.refresh(claim)
    await manager.broadcast(
        "medical",
        {"channel": "medical", "event": "medical.claim_created", "data": {"id": str(claim.id), "claim_number": claim.claim_number}},
    )
    return claim


@router.get("/claims", response_model=list[MedicalClaimResponse])
async def list_medical_claims(
    _: CurrentUser,
    session: DbSession,
    q: Search = None,
    claim_status: str | None = Query(default=None, max_length=30),
    member_id: uuid.UUID | None = None,
):
    filters = []
    if q:
        term = f"%{q.strip()}%"
        filters.append(or_(MedicalClaim.claim_number.ilike(term), MedicalClaim.provider_name.ilike(term)))
    if claim_status:
        filters.append(MedicalClaim.status == claim_status)
    if member_id:
        filters.append(MedicalClaim.member_id == member_id)
    result = await session.execute(
        select(MedicalClaim).where(*filters).order_by(MedicalClaim.created_at.desc()).limit(100)
    )
    return list(result.scalars().all())


@router.patch("/claims/{claim_id}/status", response_model=MedicalClaimResponse)
async def update_medical_claim_status(
    claim_id: uuid.UUID,
    payload: MedicalClaimStatusUpdate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
):
    claim = await session.get(MedicalClaim, claim_id)
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medical claim not found")
    allowed = {
        "submitted": {"review", "declined"},
        "review": {"approved", "declined"},
        "approved": {"paid"},
        "declined": {"closed"},
        "paid": {"closed"},
        "closed": set(),
    }
    if payload.status not in allowed.get(claim.status, set()):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Invalid medical claim transition: {claim.status} -> {payload.status}")
    if payload.status == "approved":
        if payload.approved_amount is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="approved_amount is required when approving a medical claim")
        if payload.approved_amount > claim.claim_amount:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="approved_amount cannot exceed claim_amount")
        claim.approved_amount = payload.approved_amount
    claim.status = payload.status
    await record_audit_event(
        session,
        action="medical.claim_status_changed",
        entity_type="medical_claim",
        entity_id=str(claim.id),
        actor_user_id=user.id,
        details={"status": payload.status, "approved_amount": str(payload.approved_amount) if payload.approved_amount is not None else None},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    await session.refresh(claim)
    return claim
