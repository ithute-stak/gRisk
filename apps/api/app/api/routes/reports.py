from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.models.claim import Claim
from app.models.customer import Customer
from app.models.finance import Invoice, Payment
from app.models.guarantee import Guarantee
from app.models.insurance import Policy, Quote
from app.models.medical import MedicalClaim, MedicalMember
from app.models.risk import RiskRegisterItem
from app.schemas.report import (
    ClaimsReportResponse,
    ExecutiveReportResponse,
    FinanceReportResponse,
    PortfolioReportResponse,
)

router = APIRouter(prefix="/reports", tags=["reports"])


async def _count(session: DbSession, model: Any, *filters: Any) -> int:
    value = await session.scalar(select(func.count(model.id)).where(*filters))
    return int(value or 0)


async def _sum(session: DbSession, expression: Any, *filters: Any) -> Decimal:
    value = await session.scalar(select(func.coalesce(func.sum(expression), 0)).where(*filters))
    return Decimal(value or 0)


async def _group_counts(session: DbSession, expression: Any) -> dict[str, int]:
    result = await session.execute(
        select(expression, func.count()).group_by(expression).order_by(expression)
    )
    return {str(key): int(count) for key, count in result.all() if key is not None}


@router.get("/executive", response_model=ExecutiveReportResponse)
async def executive_report(_: CurrentUser, session: DbSession):
    claim_terminal = ["settled", "closed", "rejected"]
    guarantee_terminal = ["released", "expired", "cancelled", "closed", "declined"]
    invoice_open = ["issued", "partially_paid"]

    return ExecutiveReportResponse(
        customers=await _count(session, Customer),
        active_policies=await _count(session, Policy, Policy.status == "active"),
        open_claims=await _count(session, Claim, Claim.status.notin_(claim_terminal)),
        active_medical_members=await _count(
            session,
            MedicalMember,
            MedicalMember.status == "active",
        ),
        active_guarantees=await _count(
            session,
            Guarantee,
            Guarantee.status.notin_(guarantee_terminal),
        ),
        open_risk_items=await _count(
            session,
            RiskRegisterItem,
            RiskRegisterItem.status != "closed",
        ),
        outstanding_invoices=await _count(
            session,
            Invoice,
            Invoice.status.in_(invoice_open),
            Invoice.amount_paid < Invoice.amount_due,
        ),
        total_policy_premium=await _sum(session, Policy.premium),
        total_claimed=await _sum(session, Claim.claim_amount),
        total_claim_approved=await _sum(session, func.coalesce(Claim.approved_amount, 0)),
        total_received=await _sum(session, Payment.amount),
        outstanding_balance=await _sum(
            session,
            Invoice.amount_due - Invoice.amount_paid,
            Invoice.status.in_(invoice_open),
            Invoice.amount_paid < Invoice.amount_due,
        ),
    )


@router.get("/portfolio", response_model=PortfolioReportResponse)
async def portfolio_report(_: CurrentUser, session: DbSession):
    effective_risk_level = func.coalesce(
        RiskRegisterItem.residual_level,
        RiskRegisterItem.inherent_level,
    )
    return PortfolioReportResponse(
        quotes_by_status=await _group_counts(session, Quote.status),
        policies_by_status=await _group_counts(session, Policy.status),
        claims_by_status=await _group_counts(session, Claim.status),
        medical_claims_by_status=await _group_counts(session, MedicalClaim.status),
        guarantees_by_status=await _group_counts(session, Guarantee.status),
        risk_items_by_level=await _group_counts(session, effective_risk_level),
        invoices_by_status=await _group_counts(session, Invoice.status),
    )


@router.get("/finance", response_model=FinanceReportResponse)
async def finance_report(_: CurrentUser, session: DbSession):
    today = datetime.now(UTC).date()
    active_invoice = Invoice.status != "cancelled"
    open_invoice = Invoice.status.in_(["issued", "partially_paid"])
    overdue = (
        open_invoice,
        Invoice.amount_paid < Invoice.amount_due,
        Invoice.due_date < today,
    )
    return FinanceReportResponse(
        total_invoiced=await _sum(session, Invoice.amount_due, active_invoice),
        total_received=await _sum(session, Payment.amount),
        outstanding_balance=await _sum(
            session,
            Invoice.amount_due - Invoice.amount_paid,
            open_invoice,
            Invoice.amount_paid < Invoice.amount_due,
        ),
        overdue_balance=await _sum(
            session,
            Invoice.amount_due - Invoice.amount_paid,
            *overdue,
        ),
        overdue_invoices=await _count(session, Invoice, *overdue),
        payments=await _count(session, Payment),
    )


@router.get("/claims", response_model=ClaimsReportResponse)
async def claims_report(_: CurrentUser, session: DbSession):
    general_terminal = ["settled", "closed", "rejected"]
    medical_terminal = ["paid", "closed", "declined"]
    return ClaimsReportResponse(
        general_claims=await _count(session, Claim),
        medical_claims=await _count(session, MedicalClaim),
        open_general_claims=await _count(
            session,
            Claim,
            Claim.status.notin_(general_terminal),
        ),
        open_medical_claims=await _count(
            session,
            MedicalClaim,
            MedicalClaim.status.notin_(medical_terminal),
        ),
        general_claimed=await _sum(session, Claim.claim_amount),
        general_approved=await _sum(session, func.coalesce(Claim.approved_amount, 0)),
        medical_claimed=await _sum(session, MedicalClaim.claim_amount),
        medical_approved=await _sum(
            session,
            func.coalesce(MedicalClaim.approved_amount, 0),
        ),
    )
