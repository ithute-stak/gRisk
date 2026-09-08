import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class RoleResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None


class AdminUserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=12, max_length=256)
    role_names: list[str] = Field(default_factory=list, max_length=20)
    is_active: bool = True
    is_superuser: bool = False


class AdminUserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    role_names: list[str] | None = Field(default=None, max_length=20)
    is_active: bool | None = None
    is_superuser: bool | None = None


class AdminPasswordReset(BaseModel):
    password: str = Field(min_length=12, max_length=256)


class AdminUserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool
    roles: list[str]
    created_at: datetime
    updated_at: datetime


class AdminUserListResponse(BaseModel):
    items: list[AdminUserResponse]
    total: int
    page: int
    page_size: int


class AuditEventResponse(BaseModel):
    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: str | None
    details: dict[str, Any]
    ip_address: str | None
    created_at: datetime


class AuditEventListResponse(BaseModel):
    items: list[AuditEventResponse]
    total: int
    page: int
    page_size: int
