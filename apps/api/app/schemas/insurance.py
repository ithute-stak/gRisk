import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

QuoteStatus = Literal["draft", "review", "submitted", "accepted", "declined", "expired", "converted"]
PolicyStatus = Literal["active", "pending", "expired", "cancelled", "suspended"]


class ProductCreate(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=160)
    category: str = Field(min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=5000)
    is_active: bool = True


class ProductResponse(ProductCreate):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuoteItemCreate(BaseModel):
    label: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    amount: Decimal = Field(default=Decimal("0"), ge=0)


class QuoteItemResponse(QuoteItemCreate):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuoteCreate(BaseModel):
    customer_id: uuid.UUID
    product_id: uuid.UUID
    currency: str = Field(default="LSL", min_length=3, max_length=3)
    sum_insured: Decimal = Field(default=Decimal("0"), ge=0)
    premium: Decimal = Field(default=Decimal("0"), ge=0)
    third_party_limit: Decimal | None = Field(default=None, ge=0)
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = Field(default=None, max_length=10000)
    items: list[QuoteItemCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class QuoteStatusUpdate(BaseModel):
    status: QuoteStatus


class QuoteResponse(BaseModel):
    id: uuid.UUID
    quote_number: str
    customer_id: uuid.UUID
    product_id: uuid.UUID
    status: str
    currency: str
    sum_insured: Decimal
    premium: Decimal
    third_party_limit: Decimal | None
    start_date: date | None
    end_date: date | None
    notes: str | None
    created_by_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    items: list[QuoteItemResponse]

    model_config = ConfigDict(from_attributes=True)


class QuoteListResponse(BaseModel):
    items: list[QuoteResponse]
    total: int
    page: int
    page_size: int


class PolicyCreateFromQuote(BaseModel):
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class PolicyResponse(BaseModel):
    id: uuid.UUID
    policy_number: str
    customer_id: uuid.UUID
    product_id: uuid.UUID
    source_quote_id: uuid.UUID | None
    status: str
    currency: str
    sum_insured: Decimal
    premium: Decimal
    start_date: date
    end_date: date
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
