import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

RiskAssessmentType = Literal[
    "enterprise_risk_management",
    "risk_survey",
    "alternative_risk_transfer",
    "risk_financing",
    "premium_funding",
    "general",
]
RiskAssessmentStatus = Literal["draft", "in_progress", "review", "completed", "archived"]
RiskItemStatus = Literal["open", "monitoring", "mitigated", "accepted", "closed"]


class RiskAssessmentCreate(BaseModel):
    customer_id: uuid.UUID
    assessment_type: RiskAssessmentType = "general"
    title: str = Field(min_length=2, max_length=200)
    assessment_date: date
    summary: str | None = Field(default=None, max_length=10000)
    recommendations: str | None = Field(default=None, max_length=10000)
    assigned_user_id: uuid.UUID | None = None


class RiskAssessmentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    assessment_date: date | None = None
    summary: str | None = Field(default=None, max_length=10000)
    recommendations: str | None = Field(default=None, max_length=10000)
    assigned_user_id: uuid.UUID | None = None


class RiskAssessmentStatusUpdate(BaseModel):
    status: RiskAssessmentStatus


class RiskRegisterItemCreate(BaseModel):
    category: str = Field(min_length=2, max_length=100)
    title: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    likelihood: int = Field(ge=1, le=5)
    impact: int = Field(ge=1, le=5)
    existing_controls: str | None = Field(default=None, max_length=10000)
    treatment_plan: str | None = Field(default=None, max_length=10000)
    risk_owner: str | None = Field(default=None, max_length=160)
    due_date: date | None = None
    status: RiskItemStatus = "open"
    residual_likelihood: int | None = Field(default=None, ge=1, le=5)
    residual_impact: int | None = Field(default=None, ge=1, le=5)

    @model_validator(mode="after")
    def validate_residual_pair(self):
        if (self.residual_likelihood is None) != (self.residual_impact is None):
            raise ValueError("residual_likelihood and residual_impact must be supplied together")
        return self


class RiskRegisterItemUpdate(BaseModel):
    category: str | None = Field(default=None, min_length=2, max_length=100)
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    likelihood: int | None = Field(default=None, ge=1, le=5)
    impact: int | None = Field(default=None, ge=1, le=5)
    existing_controls: str | None = Field(default=None, max_length=10000)
    treatment_plan: str | None = Field(default=None, max_length=10000)
    risk_owner: str | None = Field(default=None, max_length=160)
    due_date: date | None = None
    status: RiskItemStatus | None = None
    residual_likelihood: int | None = Field(default=None, ge=1, le=5)
    residual_impact: int | None = Field(default=None, ge=1, le=5)


class RiskRegisterItemResponse(BaseModel):
    id: uuid.UUID
    assessment_id: uuid.UUID
    category: str
    title: str
    description: str | None
    likelihood: int
    impact: int
    inherent_score: int
    inherent_level: str
    existing_controls: str | None
    treatment_plan: str | None
    risk_owner: str | None
    due_date: date | None
    status: str
    residual_likelihood: int | None
    residual_impact: int | None
    residual_score: int | None
    residual_level: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskAssessmentSummary(BaseModel):
    id: uuid.UUID
    assessment_number: str
    customer_id: uuid.UUID
    assessment_type: str
    title: str
    assessment_date: date
    status: str
    overall_level: str | None
    assigned_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskAssessmentResponse(RiskAssessmentSummary):
    summary: str | None
    recommendations: str | None
    items: list[RiskRegisterItemResponse] = Field(default_factory=list)


class RiskAssessmentListResponse(BaseModel):
    items: list[RiskAssessmentSummary]
    total: int
    page: int
    page_size: int


class RiskDashboardResponse(BaseModel):
    assessments: int
    open_items: int
    high_or_critical_items: int
    overdue_items: int
