import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

PartnerType = Literal[
    "insurer",
    "bank",
    "medical_provider",
    "payment_provider",
    "sms_provider",
    "email_provider",
    "other",
]
IntegrationStatus = Literal["not_configured", "sandbox", "active", "paused", "error"]


class PartnerCreate(BaseModel):
    partner_type: PartnerType
    name: str = Field(min_length=2, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    website: str | None = Field(default=None, max_length=500)
    external_reference: str | None = Field(default=None, max_length=160)
    integration_status: IntegrationStatus = "not_configured"
    notes: str | None = Field(default=None, max_length=5000)
    is_active: bool = True


class PartnerUpdate(BaseModel):
    partner_type: PartnerType | None = None
    name: str | None = Field(default=None, min_length=2, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    website: str | None = Field(default=None, max_length=500)
    external_reference: str | None = Field(default=None, max_length=160)
    integration_status: IntegrationStatus | None = None
    notes: str | None = Field(default=None, max_length=5000)
    is_active: bool | None = None


class PartnerResponse(BaseModel):
    id: uuid.UUID
    partner_number: str
    partner_type: str
    name: str
    email: str | None
    phone: str | None
    website: str | None
    external_reference: str | None
    integration_status: str
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PartnerListResponse(BaseModel):
    items: list[PartnerResponse]
    total: int
    page: int
    page_size: int
