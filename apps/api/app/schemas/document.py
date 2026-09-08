import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID | None
    entity_type: str
    entity_id: str | None
    category: str
    filename: str
    content_type: str
    size_bytes: int
    description: str | None
    status: str
    uploaded_by_user_id: uuid.UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int
