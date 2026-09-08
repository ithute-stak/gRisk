import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MedicalMemberStatus = Literal["active", "suspended", "expired", "cancelled"]
AuthorisationStatus = Literal["pending", "approved", "declined", "cancelled"]
MedicalClaimStatus = Literal["submitted", "review", "approved", "declined", "paid", "closed"]
MedicalClaimKind = Literal["medical", "cash_plan"]


class MedicalBenefitCreate(BaseModel):
    code: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=160)
    category: str = Field(min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=5000)
    annual_monetary_limit: Decimal | None = Field(default=None, ge=0)
    per_event_limit: Decimal | None = Field(default=None, ge=0)
    annual_visit_limit: int | None = Field(default=None, ge=0)
    requires_authorisation: bool = False
    is_active: bool = True


class MedicalBenefitResponse(MedicalBenefitCreate):
    id: uuid.UUID
    plan_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MedicalPlanCreate(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=5000)
    monthly_premium: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default="LSL", min_length=3, max_length=3)
    is_active: bool = True


class MedicalPlanResponse(MedicalPlanCreate):
    id: uuid.UUID
    benefits: list[MedicalBenefitResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MedicalMemberCreate(BaseModel):
    customer_id: uuid.UUID
    plan_id: uuid.UUID
    start_date: date
    end_date: date | None = None
    status: MedicalMemberStatus = "active"

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class MedicalMemberUpdate(BaseModel):
    plan_id: uuid.UUID | None = None
    status: MedicalMemberStatus | None = None
    start_date: date | None = None
    end_date: date | None = None


class MedicalDependantCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    relationship_type: str = Field(min_length=2, max_length=50)
    date_of_birth: date | None = None
    status: MedicalMemberStatus = "active"


class MedicalDependantResponse(MedicalDependantCreate):
    id: uuid.UUID
    member_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MedicalMemberSummary(BaseModel):
    id: uuid.UUID
    member_number: str
    customer_id: uuid.UUID
    plan_id: uuid.UUID
    status: str
    start_date: date
    end_date: date | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MedicalMemberResponse(MedicalMemberSummary):
    dependants: list[MedicalDependantResponse] = Field(default_factory=list)


class MedicalMemberListResponse(BaseModel):
    items: list[MedicalMemberSummary]
    total: int
    page: int
    page_size: int


class MedicalUtilisationCreate(BaseModel):
    member_id: uuid.UUID
    benefit_id: uuid.UUID
    dependant_id: uuid.UUID | None = None
    service_date: date
    amount: Decimal = Field(default=Decimal(0), ge=0)
    units: int = Field(default=1, ge=1)
    provider_name: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=5000)


class MedicalUtilisationResponse(BaseModel):
    id: uuid.UUID
    member_id: uuid.UUID
    benefit_id: uuid.UUID
    dependant_id: uuid.UUID | None
    service_date: date
    amount: Decimal
    units: int
    provider_name: str | None
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BenefitBalanceResponse(BaseModel):
    member_id: uuid.UUID
    benefit_id: uuid.UUID
    benefit_code: str
    benefit_name: str
    year: int
    used_amount: Decimal
    remaining_amount: Decimal | None
    used_units: int
    remaining_units: int | None


class MedicalAuthorisationCreate(BaseModel):
    member_id: uuid.UUID
    benefit_id: uuid.UUID
    dependant_id: uuid.UUID | None = None
    requested_amount: Decimal | None = Field(default=None, ge=0)
    provider_name: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=5000)


class MedicalAuthorisationDecision(BaseModel):
    status: Literal["approved", "declined", "cancelled"]
    approved_amount: Decimal | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=5000)


class MedicalAuthorisationResponse(BaseModel):
    id: uuid.UUID
    authorisation_number: str
    member_id: uuid.UUID
    benefit_id: uuid.UUID
    dependant_id: uuid.UUID | None
    status: str
    requested_amount: Decimal | None
    approved_amount: Decimal | None
    provider_name: str | None
    notes: str | None
    requested_at: datetime
    decided_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class MedicalClaimCreate(BaseModel):
    member_id: uuid.UUID
    dependant_id: uuid.UUID | None = None
    claim_kind: MedicalClaimKind = "medical"
    service_date: date
    admission_date: date | None = None
    discharge_date: date | None = None
    claim_amount: Decimal = Field(default=Decimal(0), ge=0)
    provider_name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=10000)

    @model_validator(mode="after")
    def validate_hospital_dates(self):
        if self.admission_date and self.discharge_date and self.discharge_date < self.admission_date:
            raise ValueError("discharge_date must be on or after admission_date")
        if self.claim_kind == "cash_plan" and not (self.admission_date and self.discharge_date):
            raise ValueError("cash_plan claims require admission_date and discharge_date")
        return self


class MedicalClaimStatusUpdate(BaseModel):
    status: MedicalClaimStatus
    approved_amount: Decimal | None = Field(default=None, ge=0)


class MedicalClaimResponse(BaseModel):
    id: uuid.UUID
    claim_number: str
    member_id: uuid.UUID
    dependant_id: uuid.UUID | None
    claim_kind: str
    status: str
    service_date: date
    admission_date: date | None
    discharge_date: date | None
    claim_amount: Decimal
    approved_amount: Decimal | None
    provider_name: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
