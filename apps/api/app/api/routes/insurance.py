import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models.customer import Customer
from app.models.insurance import InsuranceProduct, Policy, Quote, QuoteItem
from app.realtime.manager import manager
from app.schemas.insurance import (
    PolicyCreateFromQuote,
    PolicyResponse,
    ProductCreate,
    ProductResponse,
    QuoteCreate,
    QuoteListResponse,
    QuoteResponse,
    QuoteStatusUpdate,
)
from app.services.audit import record_audit_event

router = APIRouter(prefix="/insurance", tags=["insurance"])
Page = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]
Search = Annotated[str | None, Query(max_length=200)]


async def _get_product_or_404(session: DbSession, product_id: uuid.UUID) -> InsuranceProduct:
    product = await session.get(InsuranceProduct, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insurance product not found")
    return product


async def _get_quote_or_404(session: DbSession, quote_id: uuid.UUID) -> Quote:
    result = await session.execute(
        select(Quote).options(selectinload(Quote.items)).where(Quote.id == quote_id)
    )
    quote = result.scalar_one_or_none()
    if quote is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")
    return quote


@router.get("/products", response_model=list[ProductResponse])
async def list_products(_: CurrentUser, session: DbSession, active_only: bool = True):
    query = select(InsuranceProduct).order_by(InsuranceProduct.category, InsuranceProduct.name)
    if active_only:
        query = query.where(InsuranceProduct.is_active.is_(True))
    result = await session.execute(query)
    return list(result.scalars().all())


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
):
    existing = await session.scalar(select(InsuranceProduct).where(InsuranceProduct.code == payload.code))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Product code already exists")

    product = InsuranceProduct(**payload.model_dump())
    session.add(product)
    await session.flush()
    await record_audit_event(
        session,
        action="insurance.product_created",
        entity_type="insurance_product",
        entity_id=str(product.id),
        actor_user_id=user.id,
        details={"code": product.code, "name": product.name},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    await session.refresh(product)
    return product


@router.get("/quotes", response_model=QuoteListResponse)
async def list_quotes(
    _: CurrentUser,
    session: DbSession,
    page: Page = 1,
    page_size: PageSize = 25,
    q: Search = None,
    quote_status: str | None = Query(default=None, max_length=30),
):
    filters = []
    if q:
        term = f"%{q.strip()}%"
        filters.append(Quote.quote_number.ilike(term))
    if quote_status:
        filters.append(Quote.status == quote_status)

    total = await session.scalar(select(func.count(Quote.id)).where(*filters))
    result = await session.execute(
        select(Quote)
        .options(selectinload(Quote.items))
        .where(*filters)
        .order_by(Quote.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return QuoteListResponse(
        items=list(result.scalars().unique().all()),
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.post("/quotes", response_model=QuoteResponse, status_code=status.HTTP_201_CREATED)
async def create_quote(
    payload: QuoteCreate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
):
    customer = await session.get(Customer, payload.customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    product = await _get_product_or_404(session, payload.product_id)
    if not product.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Insurance product is inactive")

    quote = Quote(
        customer_id=payload.customer_id,
        product_id=payload.product_id,
        currency=payload.currency.upper(),
        sum_insured=payload.sum_insured,
        premium=payload.premium,
        third_party_limit=payload.third_party_limit,
        start_date=payload.start_date,
        end_date=payload.end_date,
        notes=payload.notes,
        created_by_user_id=user.id,
    )
    quote.items = [QuoteItem(**item.model_dump()) for item in payload.items]
    session.add(quote)
    await session.flush()
    await record_audit_event(
        session,
        action="insurance.quote_created",
        entity_type="quote",
        entity_id=str(quote.id),
        actor_user_id=user.id,
        details={
            "quote_number": quote.quote_number,
            "customer_id": str(customer.id),
            "product_code": product.code,
        },
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    created = await _get_quote_or_404(session, quote.id)
    await manager.broadcast(
        "quotations",
        {"channel": "quotations", "event": "quote.created", "data": {"id": str(created.id), "quote_number": created.quote_number}},
    )
    return created


@router.get("/quotes/{quote_id}", response_model=QuoteResponse)
async def get_quote(quote_id: uuid.UUID, _: CurrentUser, session: DbSession):
    return await _get_quote_or_404(session, quote_id)


@router.patch("/quotes/{quote_id}/status", response_model=QuoteResponse)
async def update_quote_status(
    quote_id: uuid.UUID,
    payload: QuoteStatusUpdate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
):
    quote = await _get_quote_or_404(session, quote_id)
    previous = quote.status
    quote.status = payload.status
    await record_audit_event(
        session,
        action="insurance.quote_status_changed",
        entity_type="quote",
        entity_id=str(quote.id),
        actor_user_id=user.id,
        details={"from": previous, "to": payload.status},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    updated = await _get_quote_or_404(session, quote.id)
    await manager.broadcast(
        "quotations",
        {"channel": "quotations", "event": "quote.status_changed", "data": {"id": str(updated.id), "status": updated.status}},
    )
    return updated


@router.post(
    "/quotes/{quote_id}/convert-to-policy",
    response_model=PolicyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def convert_quote_to_policy(
    quote_id: uuid.UUID,
    payload: PolicyCreateFromQuote,
    request: Request,
    user: CurrentUser,
    session: DbSession,
):
    quote = await _get_quote_or_404(session, quote_id)
    existing = await session.scalar(select(Policy).where(Policy.source_quote_id == quote.id))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Quote already has a policy")
    if quote.status not in {"accepted", "submitted", "review"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Quote must be accepted or under approval before conversion",
        )

    policy = Policy(
        customer_id=quote.customer_id,
        product_id=quote.product_id,
        source_quote_id=quote.id,
        currency=quote.currency,
        sum_insured=quote.sum_insured,
        premium=quote.premium,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status="active",
    )
    quote.status = "converted"
    session.add(policy)
    await session.flush()
    await record_audit_event(
        session,
        action="insurance.policy_created",
        entity_type="policy",
        entity_id=str(policy.id),
        actor_user_id=user.id,
        details={"policy_number": policy.policy_number, "source_quote_id": str(quote.id)},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    await session.refresh(policy)
    await manager.broadcast(
        "policies",
        {"channel": "policies", "event": "policy.created", "data": {"id": str(policy.id), "policy_number": policy.policy_number}},
    )
    return policy


@router.get("/policies", response_model=list[PolicyResponse])
async def list_policies(
    _: CurrentUser,
    session: DbSession,
    customer_id: uuid.UUID | None = None,
    policy_status: str | None = Query(default=None, max_length=30),
):
    filters = []
    if customer_id:
        filters.append(Policy.customer_id == customer_id)
    if policy_status:
        filters.append(Policy.status == policy_status)
    result = await session.execute(
        select(Policy).where(*filters).order_by(Policy.created_at.desc()).limit(100)
    )
    return list(result.scalars().all())
