from decimal import Decimal

from pydantic import BaseModel, Field, field_serializer


def _money(value: Decimal) -> str:
    return format(value, ".2f")


class ExecutiveReportResponse(BaseModel):
    customers: int
    active_policies: int
    open_claims: int
    active_medical_members: int
    active_guarantees: int
    open_risk_items: int
    outstanding_invoices: int
    total_policy_premium: Decimal
    total_claimed: Decimal
    total_claim_approved: Decimal
    total_received: Decimal
    outstanding_balance: Decimal

    @field_serializer(
        "total_policy_premium",
        "total_claimed",
        "total_claim_approved",
        "total_received",
        "outstanding_balance",
    )
    def serialize_money(self, value: Decimal) -> str:
        return _money(value)


class PortfolioReportResponse(BaseModel):
    quotes_by_status: dict[str, int] = Field(default_factory=dict)
    policies_by_status: dict[str, int] = Field(default_factory=dict)
    claims_by_status: dict[str, int] = Field(default_factory=dict)
    medical_claims_by_status: dict[str, int] = Field(default_factory=dict)
    guarantees_by_status: dict[str, int] = Field(default_factory=dict)
    risk_items_by_level: dict[str, int] = Field(default_factory=dict)
    invoices_by_status: dict[str, int] = Field(default_factory=dict)


class FinanceReportResponse(BaseModel):
    total_invoiced: Decimal
    total_received: Decimal
    outstanding_balance: Decimal
    overdue_balance: Decimal
    overdue_invoices: int
    payments: int

    @field_serializer(
        "total_invoiced",
        "total_received",
        "outstanding_balance",
        "overdue_balance",
    )
    def serialize_money(self, value: Decimal) -> str:
        return _money(value)


class ClaimsReportResponse(BaseModel):
    general_claims: int
    medical_claims: int
    open_general_claims: int
    open_medical_claims: int
    general_claimed: Decimal
    general_approved: Decimal
    medical_claimed: Decimal
    medical_approved: Decimal

    @field_serializer(
        "general_claimed",
        "general_approved",
        "medical_claimed",
        "medical_approved",
    )
    def serialize_money(self, value: Decimal) -> str:
        return _money(value)
