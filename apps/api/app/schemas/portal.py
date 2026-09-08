import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

PortalRole = Literal["owner", "admin", "member"]


def _money(value: Decimal) -> str:
    return format(value, ".2f")


class PortalAccessCreate(BaseModel):
    user_id: uuid.UUID
    customer_id: uuid.UUID
    portal_role: PortalRole = "member"


class PortalAccessUpdate(BaseModel):
    portal_role: PortalRole | None = None
    is_active: bool | None = None


class PortalAccessResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    customer_id: uuid.UUID
    portal_role: str
    is_active: bool
    created_by_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PortalUserSummary(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class PortalCustomerSummary(BaseModel):
    id: uuid.UUID
    customer_number: str
    display_name: str
    customer_type: str
    email: str | None
    phone: str | None
    portal_role: str


class PortalPolicySummary(BaseModel):
    id: uuid.UUID
    policy_number: str
    product_id: uuid.UUID
    status: str
    currency: str
    sum_insured: Decimal
    premium: Decimal
    start_date: date
    end_date: date

    @field_serializer("sum_insured", "premium")
    def serialize_amounts(self, value: Decimal) -> str:
        return _money(value)

    model_config = ConfigDict(from_attributes=True)


class PortalClaimSummary(BaseModel):
    id: uuid.UUID
    claim_number: str
    policy_id: uuid.UUID
    claim_type: str
    incident_date: date
    claim_amount: Decimal
    approved_amount: Decimal | None
    status: str

    @field_serializer("claim_amount", "approved_amount")
    def serialize_amounts(self, value: Decimal | None) -> str | None:
        return None if value is None else _money(value)

    model_config = ConfigDict(from_attributes=True)


class PortalMedicalMemberSummary(BaseModel):
    id: uuid.UUID
    member_number: str
    plan_id: uuid.UUID
    status: str
    start_date: date
    end_date: date | None

    model_config = ConfigDict(from_attributes=True)


class PortalGuaranteeSummary(BaseModel):
    id: uuid.UUID
    guarantee_number: str
    guarantee_type: str
    status: str
    beneficiary: str
    currency: str
    guarantee_amount: Decimal
    expiry_date: date | None

    @field_serializer("guarantee_amount")
    def serialize_amount(self, value: Decimal) -> str:
        return _money(value)

    model_config = ConfigDict(from_attributes=True)


class PortalInvoiceSummary(BaseModel):
    id: uuid.UUID
    invoice_number: str
    status: str
    invoice_type: str
    description: str
    currency: str
    amount_due: Decimal
    amount_paid: Decimal
    issue_date: date
    due_date: date

    @field_serializer("amount_due", "amount_paid")
    def serialize_amounts(self, value: Decimal) -> str:
        return _money(value)

    model_config = ConfigDict(from_attributes=True)


class PortalOverviewResponse(BaseModel):
    customer: PortalCustomerSummary
    policies: list[PortalPolicySummary] = Field(default_factory=list)
    claims: list[PortalClaimSummary] = Field(default_factory=list)
    medical_members: list[PortalMedicalMemberSummary] = Field(default_factory=list)
    guarantees: list[PortalGuaranteeSummary] = Field(default_factory=list)
    invoices: list[PortalInvoiceSummary] = Field(default_factory=list)
    outstanding_balance: Decimal
    unread_notifications: int

    @field_serializer("outstanding_balance")
    def serialize_outstanding_balance(self, value: Decimal) -> str:
        return _money(value)
