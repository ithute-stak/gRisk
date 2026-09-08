import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select

from app.api.deps import CurrentUser, DbSession
from app.models.customer import Customer
from app.models.document import Document
from app.schemas.document import DocumentListResponse, DocumentResponse
from app.services.audit import record_audit_event
from app.services.document_storage import DocumentTooLargeError, document_path, save_upload

router = APIRouter(prefix="/documents", tags=["documents"])
Page = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]
Search = Annotated[str | None, Query(max_length=200)]

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "text/plain",
    "text/csv",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


async def _document_or_404(session: DbSession, document_id: uuid.UUID) -> Document:
    document = await session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    _: CurrentUser,
    session: DbSession,
    page: Page = 1,
    page_size: PageSize = 25,
    q: Search = None,
    customer_id: uuid.UUID | None = None,
    category: str | None = Query(default=None, max_length=64),
    entity_type: str | None = Query(default=None, max_length=64),
    document_status: str | None = Query(default="active", max_length=24),
) -> DocumentListResponse:
    filters = []
    if q:
        term = f"%{q.strip()}%"
        filters.append(
            or_(
                Document.filename.ilike(term),
                Document.description.ilike(term),
                Document.category.ilike(term),
                Document.entity_id.ilike(term),
            )
        )
    if customer_id:
        filters.append(Document.customer_id == customer_id)
    if category:
        filters.append(Document.category == category)
    if entity_type:
        filters.append(Document.entity_type == entity_type)
    if document_status:
        filters.append(Document.status == document_status)

    total = await session.scalar(select(func.count(Document.id)).where(*filters)) or 0
    result = await session.execute(
        select(Document)
        .where(*filters)
        .order_by(Document.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return DocumentListResponse(
        items=list(result.scalars().all()),
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    user: CurrentUser,
    session: DbSession,
    file: Annotated[UploadFile, File()],
    customer_id: Annotated[uuid.UUID | None, Form()] = None,
    entity_type: Annotated[str, Form(max_length=64)] = "customer",
    entity_id: Annotated[str | None, Form(max_length=100)] = None,
    category: Annotated[str, Form(max_length=64)] = "general",
    description: Annotated[str | None, Form(max_length=5000)] = None,
) -> DocumentResponse:
    filename = Path(file.filename or "document").name.strip()
    if not filename:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="A file name is required")
    content_type = (file.content_type or "application/octet-stream").lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported document type. Upload PDF, image, text, Word or Excel files.",
        )
    if customer_id and await session.get(Customer, customer_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    try:
        storage_key, size_bytes = await save_upload(file)
    except DocumentTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(exc)) from exc

    document = Document(
        customer_id=customer_id,
        entity_type=entity_type.strip().lower() or "customer",
        entity_id=entity_id.strip() if entity_id else None,
        category=category.strip().lower() or "general",
        filename=filename,
        content_type=content_type,
        size_bytes=size_bytes,
        storage_key=storage_key,
        description=description.strip() if description else None,
        uploaded_by_user_id=user.id,
    )
    session.add(document)
    try:
        await session.flush()
        await record_audit_event(
            session,
            action="document.uploaded",
            entity_type="document",
            entity_id=str(document.id),
            actor_user_id=user.id,
            details={
                "filename": document.filename,
                "category": document.category,
                "customer_id": str(customer_id) if customer_id else None,
                "size_bytes": size_bytes,
            },
            ip_address=request.client.host if request.client else None,
        )
        await session.commit()
    except Exception:
        document_path(storage_key).unlink(missing_ok=True)
        raise
    await session.refresh(document)
    return document


@router.get("/{document_id}/download")
async def download_document(document_id: uuid.UUID, _: CurrentUser, session: DbSession):
    document = await _document_or_404(session, document_id)
    path = document_path(document.storage_key)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored document file is missing")
    return FileResponse(
        path,
        media_type=document.content_type,
        filename=document.filename,
        content_disposition_type="attachment",
    )


@router.patch("/{document_id}/archive", response_model=DocumentResponse)
async def archive_document(
    document_id: uuid.UUID,
    request: Request,
    user: CurrentUser,
    session: DbSession,
) -> DocumentResponse:
    document = await _document_or_404(session, document_id)
    document.status = "archived"
    await record_audit_event(
        session,
        action="document.archived",
        entity_type="document",
        entity_id=str(document.id),
        actor_user_id=user.id,
        details={"filename": document.filename},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    await session.refresh(document)
    return document
