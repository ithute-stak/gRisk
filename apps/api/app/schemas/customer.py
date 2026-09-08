import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

CustomerType = Literal["individual", "company"]
CustomerStatus = Literal["active", "inactive", "prospect", "suspended"]


class CustomerContactCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    role: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)


class CustomerContactResponse(CustomerContactCreate):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerAddressCreate(BaseModel):
    address_type: str = Field(default="physical", min_length=2, max_length=40)
    line1: str = Field(min_length=2, max_length=200)
    line2: str | None = Field(default=None, max_length=200)
    city: str | None = Field(default=None, max_length=120)
    district: str | None = Field(default=None, max_length=120)
    postal_code: str | None = Field(default=None, max_length=40)
    country: str = Field(default="Lesotho", min_length=2, max_length=120)


class CustomerAddressResponse(CustomerAddressCreate):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerNoteCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class CustomerNoteResponse(CustomerNoteCreate):
    id: uuid.UUID
    author_user_id: uuid.UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerCreate(BaseModel):
    customer_type: CustomerType
    display_name: str | None = Field(default=None, max_length=200)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    company_name: str | None = Field(default=None, max_length=200)
    registration_number: str | None = Field(default=None, max_length=100)
    tax_number: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    status: CustomerStatus = "active"

    @model_validator(mode="after")
    def validate_identity(self):
        if self.customer_type == "company":
            if not (self.company_name or self.display_name):
                raise ValueError("Company customers require company_name or display_name")
        elif not (self.display_name or self.first_name or self.last_name):
            raise ValueError("Individual customers require a name")
        return self


class CustomerUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=200)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    company_name: str | None = Field(default=None, max_length=200)
    registration_number: str | None = Field(default=None, max_length=100)
    tax_number: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    status: CustomerStatus | None = None


class CustomerSummary(BaseModel):
    id: uuid.UUID
    customer_number: str
    customer_type: str
    display_name: str
    email: EmailStr | None
    phone: str | None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerResponse(CustomerSummary):
    first_name: str | None
    last_name: str | None
    company_name: str | None
    registration_number: str | None
    tax_number: str | None
    updated_at: datetime
    contacts: list[CustomerContactResponse]
    addresses: list[CustomerAddressResponse]
    notes: list[CustomerNoteResponse]


class CustomerListResponse(BaseModel):
    items: list[CustomerSummary]
    total: int
    page: int
    page_size: int
