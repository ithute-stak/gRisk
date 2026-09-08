import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

InvoiceType = Literal["premium", "medical", "service_fee", "guarantee_fee", "other"]
InvoiceStatus = Literal["draft", "issued", "partially_paid", "paid", "cancelled"]
PaymentMethod = Literal["cash", "bank_transfer", "card", "mobile_money", "cheque", "other"]


class InvoiceCreate(BaseModel):
    customer_id: uuid.UUID
    policy_id: uuid.UUID | None = None
    medical_member_id: uuid.UUID | None = None
    invoice_type: InvoiceType = "premium"
    description: str = Field(min_length=2, max_length=500)
    currency: str = Field(default="LSL", min_length=3, max_length=3)
    amount_due: Decimal = Field(gt=0)
    issue_date: date
    due_date: date
    notes: str | None = Field(default=None, max_length=10000)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.due_date < self.issue_date:
            raise ValueError("due_date must be on or after issue_date")
        return self


class InvoiceUpdate(BaseModel):
    description: str | None = Field(default=None, min_length=2, max_length=500)
    due_date: date | None = None
    notes: str | None = Field(default=None, max_length=10000)


class InvoiceStatusUpdate(BaseModel):
    status: Literal["issued", "cancelled"]


class PaymentCreate(BaseModel):
    invoice_id: uuid.UUID
    amount: Decimal = Field(gt=0)
    payment_date: date
    payment_method: PaymentMethod
    reference: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=10000)


class PaymentResponse(BaseModel):
    id: uuid.UUID
    payment_number: str
    invoice_id: uuid.UUID
    customer_id: uuid.UUID
    amount: Decimal
    currency: str
    payment_date: date
    payment_method: str
    reference: str | None
    notes: str | None
    received_by_user_id: uuid.UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvoiceSummary(BaseModel):
    id: uuid.UUID
    invoice_number: str
    customer_id: uuid.UUID
    policy_id: uuid.UUID | None
    medical_member_id: uuid.UUID | None
    status: str
    invoice_type: str
    description: str
    currency: str
    amount_due: Decimal
    amount_paid: Decimal
    issue_date: date
    due_date: date
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvoiceResponse(InvoiceSummary):
    notes: str | None
    payments: list[PaymentResponse] = Field(default_factory=list)


class InvoiceListResponse(BaseModel):
    items: list[InvoiceSummary]
    total: int
    page: int
    page_size: int


class FinanceDashboardResponse(BaseModel):
    invoices: int
    outstanding_invoices: int
    overdue_invoices: int
    currency: str = "LSL"
    total_invoiced: Decimal
    total_received: Decimal
    outstanding_balance: Decimal
