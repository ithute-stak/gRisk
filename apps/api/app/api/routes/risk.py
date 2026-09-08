import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models.customer import Customer
from app.models.risk import RiskAssessment, RiskRegisterItem
from app.realtime.manager import manager
from app.schemas.risk import (
    RiskAssessmentCreate,
    RiskAssessmentListResponse,
    RiskAssessmentResponse,
    RiskAssessmentStatusUpdate,
    RiskAssessmentUpdate,
    RiskDashboardResponse,
    RiskRegisterItemCreate,
    RiskRegisterItemResponse,
    RiskRegisterItemUpdate,
)
from app.services.audit import record_audit_event

router = APIRouter(prefix="/risk", tags=["risk-management"])
Page = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]
Search = Annotated[str | None, Query(max_length=200)]

ASSESSMENT_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"in_progress", "archived"},
    "in_progress": {"review", "archived"},
    "review": {"in_progress", "completed", "archived"},
    "completed": {"archived"},
    "archived": set(),
}


def risk_level(score: int) -> str:
    if score <= 4:
        return "low"
    if score <= 9:
        return "moderate"
    if score <= 16:
        return "high"
    return "critical"


def _assessment_options():
    return (selectinload(RiskAssessment.items),)


async def _get_assessment_or_404(session: DbSession, assessment_id: uuid.UUID) -> RiskAssessment:
    result = await session.execute(
        select(RiskAssessment)
        .options(*_assessment_options())
        .where(RiskAssessment.id == assessment_id)
    )
    assessment = result.scalar_one_or_none()
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk assessment not found")
    return assessment


async def _recompute_overall_level(session: DbSession, assessment_id: uuid.UUID) -> str | None:
    result = await session.execute(
        select(RiskRegisterItem).where(
            RiskRegisterItem.assessment_id == assessment_id,
            RiskRegisterItem.status != "closed",
        )
    )
    items = list(result.scalars().all())
    assessment = await session.get(RiskAssessment, assessment_id)
    if assessment is None:
        return None
    if not items:
        assessment.overall_level = None
        return None
    max_score = max(
        item.residual_score if item.residual_score is not None else item.inherent_score for item in items
    )
    assessment.overall_level = risk_level(max_score)
    return assessment.overall_level


@router.get("/dashboard", response_model=RiskDashboardResponse)
async def risk_dashboard(_: CurrentUser, session: DbSession):
    assessments = await session.scalar(select(func.count(RiskAssessment.id))) or 0
    open_items = await session.scalar(
        select(func.count(RiskRegisterItem.id)).where(RiskRegisterItem.status != "closed")
    ) or 0
    high_or_critical = await session.scalar(
        select(func.count(RiskRegisterItem.id)).where(
            RiskRegisterItem.status != "closed",
            or_(
                RiskRegisterItem.residual_level.in_(["high", "critical"]),
                RiskRegisterItem.residual_level.is_(None)
                & RiskRegisterItem.inherent_level.in_(["high", "critical"]),
            ),
        )
    ) or 0
    overdue = await session.scalar(
        select(func.count(RiskRegisterItem.id)).where(
            RiskRegisterItem.status.notin_(["mitigated", "accepted", "closed"]),
            RiskRegisterItem.due_date.is_not(None),
            RiskRegisterItem.due_date < datetime.now(UTC).date(),
        )
    ) or 0
    return RiskDashboardResponse(
        assessments=assessments,
        open_items=open_items,
        high_or_critical_items=high_or_critical,
        overdue_items=overdue,
    )


@router.get("/assessments", response_model=RiskAssessmentListResponse)
async def list_assessments(
    _: CurrentUser,
    session: DbSession,
    page: Page = 1,
    page_size: PageSize = 25,
    q: Search = None,
    assessment_status: str | None = Query(default=None, max_length=30),
    assessment_type: str | None = Query(default=None, max_length=80),
    customer_id: uuid.UUID | None = None,
):
    filters = []
    if q:
        term = f"%{q.strip()}%"
        filters.append(
            or_(
                RiskAssessment.assessment_number.ilike(term),
                RiskAssessment.title.ilike(term),
                RiskAssessment.summary.ilike(term),
            )
        )
    if assessment_status:
        filters.append(RiskAssessment.status == assessment_status)
    if assessment_type:
        filters.append(RiskAssessment.assessment_type == assessment_type)
    if customer_id:
        filters.append(RiskAssessment.customer_id == customer_id)

    total = await session.scalar(select(func.count(RiskAssessment.id)).where(*filters))
    result = await session.execute(
        select(RiskAssessment)
        .where(*filters)
        .order_by(RiskAssessment.assessment_date.desc(), RiskAssessment.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return RiskAssessmentListResponse(
        items=list(result.scalars().all()),
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.post("/assessments", response_model=RiskAssessmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assessment(
    payload: RiskAssessmentCreate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
):
    customer = await session.get(Customer, payload.customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    assessment = RiskAssessment(**payload.model_dump(), created_by_user_id=user.id)
    session.add(assessment)
    await session.flush()
    await record_audit_event(
        session,
        action="risk.assessment_created",
        entity_type="risk_assessment",
        entity_id=str(assessment.id),
        actor_user_id=user.id,
        details={
            "assessment_number": assessment.assessment_number,
            "assessment_type": assessment.assessment_type,
            "customer_id": str(customer.id),
        },
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    created = await _get_assessment_or_404(session, assessment.id)
    await manager.broadcast(
        "risk",
        {
            "channel": "risk",
            "event": "risk.assessment_created",
            "data": {"id": str(created.id), "assessment_number": created.assessment_number},
        },
    )
    return created


@router.get("/assessments/{assessment_id}", response_model=RiskAssessmentResponse)
async def get_assessment(assessment_id: uuid.UUID, _: CurrentUser, session: DbSession):
    return await _get_assessment_or_404(session, assessment_id)


@router.patch("/assessments/{assessment_id}", response_model=RiskAssessmentResponse)
async def update_assessment(
    assessment_id: uuid.UUID,
    payload: RiskAssessmentUpdate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
):
    assessment = await _get_assessment_or_404(session, assessment_id)
    if assessment.status == "archived":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Archived assessments cannot be edited")
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(assessment, field, value)
    await record_audit_event(
        session,
        action="risk.assessment_updated",
        entity_type="risk_assessment",
        entity_id=str(assessment.id),
        actor_user_id=user.id,
        details={"changed_fields": sorted(changes)},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    return await _get_assessment_or_404(session, assessment.id)


@router.patch("/assessments/{assessment_id}/status", response_model=RiskAssessmentResponse)
async def update_assessment_status(
    assessment_id: uuid.UUID,
    payload: RiskAssessmentStatusUpdate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
):
    assessment = await _get_assessment_or_404(session, assessment_id)
    previous = assessment.status
    if payload.status not in ASSESSMENT_TRANSITIONS.get(previous, set()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid risk assessment transition: {previous} -> {payload.status}",
        )
    if payload.status == "completed" and not assessment.items:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Risk assessment must contain at least one risk item before completion",
        )
    assessment.status = payload.status
    await record_audit_event(
        session,
        action="risk.assessment_status_changed",
        entity_type="risk_assessment",
        entity_id=str(assessment.id),
        actor_user_id=user.id,
        details={"from": previous, "to": payload.status},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    updated = await _get_assessment_or_404(session, assessment.id)
    await manager.broadcast(
        "risk",
        {
            "channel": "risk",
            "event": "risk.assessment_status_changed",
            "data": {"id": str(updated.id), "status": updated.status},
        },
    )
    return updated


@router.post(
    "/assessments/{assessment_id}/items",
    response_model=RiskRegisterItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_risk_item(
    assessment_id: uuid.UUID,
    payload: RiskRegisterItemCreate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
):
    assessment = await _get_assessment_or_404(session, assessment_id)
    if assessment.status not in {"draft", "in_progress", "review"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Risk items cannot be added to a completed or archived assessment",
        )
    inherent_score = payload.likelihood * payload.impact
    residual_score = None
    residual_level = None
    if payload.residual_likelihood is not None and payload.residual_impact is not None:
        residual_score = payload.residual_likelihood * payload.residual_impact
        residual_level = risk_level(residual_score)
    item = RiskRegisterItem(
        assessment_id=assessment.id,
        **payload.model_dump(),
        inherent_score=inherent_score,
        inherent_level=risk_level(inherent_score),
        residual_score=residual_score,
        residual_level=residual_level,
    )
    session.add(item)
    await session.flush()
    await _recompute_overall_level(session, assessment.id)
    await record_audit_event(
        session,
        action="risk.item_created",
        entity_type="risk_register_item",
        entity_id=str(item.id),
        actor_user_id=user.id,
        details={
            "assessment_id": str(assessment.id),
            "category": item.category,
            "inherent_score": item.inherent_score,
            "inherent_level": item.inherent_level,
        },
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    await session.refresh(item)
    await manager.broadcast(
        "risk",
        {
            "channel": "risk",
            "event": "risk.item_created",
            "data": {"assessment_id": str(assessment.id), "id": str(item.id), "level": item.inherent_level},
        },
    )
    return item


@router.patch("/items/{item_id}", response_model=RiskRegisterItemResponse)
async def update_risk_item(
    item_id: uuid.UUID,
    payload: RiskRegisterItemUpdate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
):
    item = await session.get(RiskRegisterItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk register item not found")
    assessment = await _get_assessment_or_404(session, item.assessment_id)
    if assessment.status == "archived":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Archived risk assessments cannot be edited")
    changes = payload.model_dump(exclude_unset=True)
    likelihood = changes.get("likelihood", item.likelihood)
    impact = changes.get("impact", item.impact)
    residual_likelihood = changes.get("residual_likelihood", item.residual_likelihood)
    residual_impact = changes.get("residual_impact", item.residual_impact)
    if (residual_likelihood is None) != (residual_impact is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="residual_likelihood and residual_impact must be supplied together",
        )
    for field, value in changes.items():
        setattr(item, field, value)
    item.inherent_score = likelihood * impact
    item.inherent_level = risk_level(item.inherent_score)
    if residual_likelihood is None:
        item.residual_score = None
        item.residual_level = None
    else:
        item.residual_score = residual_likelihood * residual_impact
        item.residual_level = risk_level(item.residual_score)
    await _recompute_overall_level(session, item.assessment_id)
    await record_audit_event(
        session,
        action="risk.item_updated",
        entity_type="risk_register_item",
        entity_id=str(item.id),
        actor_user_id=user.id,
        details={
            "changed_fields": sorted(changes),
            "inherent_score": item.inherent_score,
            "residual_score": item.residual_score,
        },
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    await session.refresh(item)
    return item