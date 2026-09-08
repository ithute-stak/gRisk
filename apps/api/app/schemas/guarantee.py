import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

GuaranteeType = Literal[
    "bid_security",
    "advance_payment_guarantee",
    "performance_bond_guarantee",
    "retention_guarantee",
    "customs_excise_bond",
]
GuaranteeStatus = Literal[
    "draft",
    "review",
    "submitted",
    "approved",
    "declined",
    "issued",
    "released",
    "expired",
    "cancelled",
    "closed",
]


class GuaranteeCreate(BaseModel):
    customer_id: uuid.UUID
    guarantee_type: GuaranteeType
    beneficiary: str = Field(min_length=2, max_length=200)
    principal: str | None = Field(default=None, max_length=200)
    tender_reference: str | None = Field(default=None, max_length=120)
    contract_reference: str | None = Field(default=None, max_length=120)
    contract_description: str | None = Field(default=None, max_length=10000)
    currency: str = Field(default="LSL", min_length=3, max_length=3)
    contract_value: Decimal | None = Field(default=None, ge=0)
    guarantee_amount: Decimal = Field(ge=0)
    issuer_name: str | None = Field(default=None, max_length=200)
    effective_date: date | None = None
    expiry_date: date | None = None
    notes: str | None = Field(default=None, max_length=10000)
    assigned_user_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def validate_values(self):
        if self.contract_value is not None and self.guarantee_amount > self.contract_value:
            raise ValueError("guarantee_amount cannot exceed contract_value")
        if self.effective_date and self.expiry_date and self.expiry_date < self.effective_date:
            raise ValueError("expiry_date must be on or after effective_date")
        return self


class GuaranteeUpdate(BaseModel):
    beneficiary: str | None = Field(default=None, min_length=2, max_length=200)
    principal: str | None = Field(default=None, max_length=200)
    tender_reference: str | None = Field(default=None, max_length=120)
    contract_reference: str | None = Field(default=None, max_length=120)
    contract_description: str | None = Field(default=None, max_length=10000)
    contract_value: Decimal | None = Field(default=None, ge=0)
    guarantee_amount: Decimal | None = Field(default=None, ge=0)
    issuer_name: str | None = Field(default=None, max_length=200)
    effective_date: date | None = None
    expiry_date: date | None = None
    notes: str | None = Field(default=None, max_length=10000)
    assigned_user_id: uuid.UUID | None = None


class GuaranteeStatusUpdate(BaseModel):
    status: GuaranteeStatus
    note: str | None = Field(default=None, max_length=5000)


class GuaranteeEventResponse(BaseModel):
    id: uuid.UUID
    event_type: str
    note: str | None
    from_status: str | None
    to_status: str | None
    actor_user_id: uuid.UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GuaranteeSummary(BaseModel):
    id: uuid.UUID
    guarantee_number: str
    customer_id: uuid.UUID
    guarantee_type: str
    status: str
    beneficiary: str
    principal: str | None
    tender_reference: str | None
    contract_reference: str | None
    currency: str
    contract_value: Decimal | None
    guarantee_amount: Decimal
    issuer_name: str | None
    effective_date: date | None
    expiry_date: date | None
    assigned_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GuaranteeResponse(GuaranteeSummary):
    contract_description: str | None
    notes: str | None
    events: list[GuaranteeEventResponse] = Field(default_factory=list)


class GuaranteeListResponse(BaseModel):
    items: list[GuaranteeSummary]
    total: int
    page: int
    page_size: int
