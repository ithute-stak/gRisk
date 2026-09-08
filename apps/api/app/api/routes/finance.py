import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models.customer import Customer
from app.models.finance import Invoice, Payment
from app.models.insurance import Policy
from app.models.medical import MedicalMember
from app.realtime.manager import manager
from app.schemas.finance import (
    FinanceDashboardResponse,
    InvoiceCreate,
    InvoiceListResponse,
    InvoiceResponse,
    InvoiceStatusUpdate,
    InvoiceUpdate,
    PaymentCreate,
    PaymentResponse,
)
from app.services.audit import record_audit_event
from app.services.notifications import notify_customer_portal_users

router = APIRouter(prefix="/finance", tags=["finance"])
Page = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]
Search = Annotated[str | None, Query(max_length=200)]


def _invoice_options():
    return (selectinload(Invoice.payments),)


async def _get_invoice_or_404(session: DbSession, invoice_id: uuid.UUID) -> Invoice:
    result = await session.execute(
        select(Invoice).options(*_invoice_options()).where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


def _outstanding(invoice: Invoice) -> Decimal:
    return max(Decimal(0), invoice.amount_due - invoice.amount_paid)


@router.get("/dashboard", response_model=FinanceDashboardResponse)
async def finance_dashboard(_: CurrentUser, session: DbSession):
    active_filter = Invoice.status != "cancelled"
    invoices = await session.scalar(select(func.count(Invoice.id)).where(active_filter)) or 0
    outstanding_invoices = await session.scalar(
        select(func.count(Invoice.id)).where(
            Invoice.status.in_(["issued", "partially_paid"]),
            Invoice.amount_paid < Invoice.amount_due,
        )
    ) or 0
    overdue_invoices = await session.scalar(
        select(func.count(Invoice.id)).where(
            Invoice.status.in_(["issued", "partially_paid"]),
            Invoice.amount_paid < Invoice.amount_due,
            Invoice.due_date < datetime.now(UTC).date(),
        )
    ) or 0
    total_invoiced = await session.scalar(
        select(func.coalesce(func.sum(Invoice.amount_due), 0)).where(active_filter)
    ) or Decimal(0)
    total_received = await session.scalar(select(func.coalesce(func.sum(Payment.amount), 0))) or Decimal(0)
    outstanding_balance = await session.scalar(
        select(func.coalesce(func.sum(Invoice.amount_due - Invoice.amount_paid), 0)).where(
            Invoice.status.in_(["issued", "partially_paid"])
        )
    ) or Decimal(0)
    return FinanceDashboardResponse(
        invoices=invoices,
        outstanding_invoices=outstanding_invoices,
        overdue_invoices=overdue_invoices,
        total_invoiced=total_invoiced,
        total_received=total_received,
        outstanding_balance=outstanding_balance,
    )


@router.get("/invoices", response_model=InvoiceListResponse)
async def list_invoices(
    _: CurrentUser,
    session: DbSession,
    page: Page = 1,
    page_size: PageSize = 25,
    q: Search = None,
    invoice_status: str | None = Query(default=None, max_length=30),
    invoice_type: str | None = Query(default=None, max_length=50),
    customer_id: uuid.UUID | None = None,
):
    filters = []
    if q:
        term = f"%{q.strip()}%"
        filters.append(or_(Invoice.invoice_number.ilike(term), Invoice.description.ilike(term)))
    if invoice_status:
        filters.append(Invoice.status == invoice_status)
    if invoice_type:
        filters.append(Invoice.invoice_type == invoice_type)
    if customer_id:
        filters.append(Invoice.customer_id == customer_id)
    total = await session.scalar(select(func.count(Invoice.id)).where(*filters)) or 0
    result = await session.execute(
        select(Invoice)
        .where(*filters)
        .order_by(Invoice.issue_date.desc(), Invoice.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return InvoiceListResponse(
        items=list(result.scalars().all()),
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    payload: InvoiceCreate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
):
    customer = await session.get(Customer, payload.customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    if payload.policy_id is not None:
        policy = await session.get(Policy, payload.policy_id)
        if policy is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
        if policy.customer_id != payload.customer_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Policy does not belong to customer",
            )
    if payload.medical_member_id is not None:
        member = await session.get(MedicalMember, payload.medical_member_id)
        if member is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medical member not found")
        if member.customer_id != payload.customer_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Medical member does not belong to customer",
            )

    invoice = Invoice(
        **payload.model_dump(exclude={"currency"}),
        currency=payload.currency.upper(),
        created_by_user_id=user.id,
    )
    session.add(invoice)
    await session.flush()
    await record_audit_event(
        session,
        action="finance.invoice_created",
        entity_type="invoice",
        entity_id=str(invoice.id),
        actor_user_id=user.id,
        details={
            "invoice_number": invoice.invoice_number,
            "customer_id": str(invoice.customer_id),
            "amount_due": str(invoice.amount_due),
        },
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    created = await _get_invoice_or_404(session, invoice.id)
    await manager.broadcast(
        "finance",
        {
            "channel": "finance",
            "event": "invoice.created",
            "data": {"id": str(created.id), "invoice_number": created.invoice_number},
        },
    )
    return created


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(invoice_id: uuid.UUID, _: CurrentUser, session: DbSession):
    return await _get_invoice_or_404(session, invoice_id)


@router.patch("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: uuid.UUID,
    payload: InvoiceUpdate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
):
    invoice = await _get_invoice_or_404(session, invoice_id)
    if invoice.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft invoices can be edited",
        )
    changes = payload.model_dump(exclude_unset=True)
    issue_date = invoice.issue_date
    due_date = changes.get("due_date", invoice.due_date)
    if due_date < issue_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="due_date must be on or after issue_date",
        )
    for field, value in changes.items():
        setattr(invoice, field, value)
    await record_audit_event(
        session,
        action="finance.invoice_updated",
        entity_type="invoice",
        entity_id=str(invoice.id),
        actor_user_id=user.id,
        details={"changed_fields": sorted(changes)},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    return await _get_invoice_or_404(session, invoice.id)


@router.patch("/invoices/{invoice_id}/status", response_model=InvoiceResponse)
async def update_invoice_status(
    invoice_id: uuid.UUID,
    payload: InvoiceStatusUpdate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
):
    invoice = await _get_invoice_or_404(session, invoice_id)
    previous = invoice.status
    if payload.status == "issued" and previous != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft invoices can be issued",
        )
    if (
        payload.status == "cancelled"
        and (previous not in {"draft", "issued"} or invoice.amount_paid > 0)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Paid or partially paid invoices cannot be cancelled",
        )
    invoice.status = payload.status
    notifications = []
    if payload.status == "issued":
        notifications = await notify_customer_portal_users(
            session,
            customer_id=invoice.customer_id,
            category="finance",
            title=f"Invoice {invoice.invoice_number} issued",
            message=(
                f"A new invoice for {invoice.currency} {invoice.amount_due} has been issued "
                f"and is due on {invoice.due_date.isoformat()}."
            ),
            action_url="/portal",
        )
    await record_audit_event(
        session,
        action="finance.invoice_status_changed",
        entity_type="invoice",
        entity_id=str(invoice.id),
        actor_user_id=user.id,
        details={"from": previous, "to": invoice.status},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    updated = await _get_invoice_or_404(session, invoice.id)
    await manager.broadcast(
        "finance",
        {
            "channel": "finance",
            "event": "invoice.status_changed",
            "data": {"id": str(updated.id), "status": updated.status},
        },
    )
    for notification in notifications:
        await manager.broadcast(
            f"notifications:{notification.user_id}",
            {
                "channel": f"notifications:{notification.user_id}",
                "event": "notification.created",
                "data": {"id": str(notification.id), "title": notification.title},
            },
        )
    return updated


@router.post("/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def record_payment(
    payload: PaymentCreate,
    request: Request,
    user: CurrentUser,
    session: DbSession,
):
    invoice = await _get_invoice_or_404(session, payload.invoice_id)
    if invoice.status not in {"issued", "partially_paid"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payments can only be recorded against issued invoices",
        )
    outstanding = _outstanding(invoice)
    if payload.amount > outstanding:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Payment exceeds outstanding balance of {outstanding}",
        )
    payment = Payment(
        invoice_id=invoice.id,
        customer_id=invoice.customer_id,
        amount=payload.amount,
        currency=invoice.currency,
        payment_date=payload.payment_date,
        payment_method=payload.payment_method,
        reference=payload.reference,
        notes=payload.notes,
        received_by_user_id=user.id,
    )
    session.add(payment)
    invoice.amount_paid += payload.amount
    invoice.status = "paid" if invoice.amount_paid >= invoice.amount_due else "partially_paid"
    await session.flush()
    notifications = await notify_customer_portal_users(
        session,
        customer_id=invoice.customer_id,
        category="finance",
        title=f"Payment received for {invoice.invoice_number}",
        message=(
            f"Payment of {invoice.currency} {payment.amount} was received. "
            f"Outstanding balance: {invoice.currency} {_outstanding(invoice)}."
        ),
        action_url="/portal",
    )
    await record_audit_event(
        session,
        action="finance.payment_recorded",
        entity_type="payment",
        entity_id=str(payment.id),
        actor_user_id=user.id,
        details={
            "payment_number": payment.payment_number,
            "invoice_id": str(invoice.id),
            "amount": str(payment.amount),
            "invoice_status": invoice.status,
        },
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    await session.refresh(payment)
    await manager.broadcast(
        "finance",
        {
            "channel": "finance",
            "event": "payment.recorded",
            "data": {
                "id": str(payment.id),
                "invoice_id": str(invoice.id),
                "amount": str(payment.amount),
            },
        },
    )
    for notification in notifications:
        await manager.broadcast(
            f"notifications:{notification.user_id}",
            {
                "channel": f"notifications:{notification.user_id}",
                "event": "notification.created",
                "data": {"id": str(notification.id), "title": notification.title},
            },
        )
    return payment
