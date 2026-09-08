import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ClaimStatus = Literal[
    "reported",
    "triage",
    "documents_pending",
    "assessment",
    "insurer_review",
    "approved",
    "rejected",
    "settled",
    "closed",
]
ClaimPriority = Literal["low", "normal", "high", "critical"]


class ClaimCreate(BaseModel):
    policy_id: uuid.UUID
    claim_type: str = Field(default="general", min_length=2, max_length=60)
    incident_date: date
    description: str = Field(min_length=5, max_length=10000)
    claim_amount: Decimal = Field(default=Decimal(0), ge=0)
    priority: ClaimPriority = "normal"


class ClaimStatusUpdate(BaseModel):
    status: ClaimStatus
    note: str | None = Field(default=None, max_length=5000)
    approved_amount: Decimal | None = Field(default=None, ge=0)


class ClaimNoteCreate(BaseModel):
    note: str = Field(min_length=1, max_length=5000)


class ClaimEventResponse(BaseModel):
    id: uuid.UUID
    event_type: str
    note: str | None
    from_status: str | None
    to_status: str | None
    actor_user_id: uuid.UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClaimSummary(BaseModel):
    id: uuid.UUID
    claim_number: str
    policy_id: uuid.UUID
    customer_id: uuid.UUID
    claim_type: str
    incident_date: date
    description: str
    claim_amount: Decimal
    approved_amount: Decimal | None
    status: str
    priority: str
    assigned_user_id: uuid.UUID | None
    reported_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClaimResponse(ClaimSummary):
    events: list[ClaimEventResponse]


class ClaimListResponse(BaseModel):
    items: list[ClaimSummary]
    total: int
    page: int
    page_size: int
