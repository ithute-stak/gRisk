import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

NotificationStatus = Literal["unread", "read", "archived"]
NotificationCategory = Literal[
    "general",
    "finance",
    "policy",
    "claim",
    "medical",
    "guarantee",
    "risk",
    "portal",
]


class NotificationCreate(BaseModel):
    user_id: uuid.UUID
    customer_id: uuid.UUID | None = None
    category: NotificationCategory = "general"
    title: str = Field(min_length=2, max_length=200)
    message: str = Field(min_length=2, max_length=10000)
    action_url: str | None = Field(default=None, max_length=500)


class NotificationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    customer_id: uuid.UUID | None
    category: str
    title: str
    message: str
    status: str
    action_url: str | None
    created_at: datetime
    read_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    unread: int
