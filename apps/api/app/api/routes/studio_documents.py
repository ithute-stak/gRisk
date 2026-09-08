import re
import uuid
from html import unescape
from io import BytesIO

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, LETTER, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy import and_, delete, or_, select

from app.api.deps import CurrentUser, DbSession
from app.models.identity import User
from app.models.studio import StudioCollaborator, StudioDocument, StudioRevision
from app.services.audit import record_audit_event

router = APIRouter(prefix="/document-studio/documents", tags=["document-studio"])


class StudioCreate(BaseModel):
    title: str = Field(default="Untitled document", min_length=1, max_length=240)
    template_key: str = Field(default="blank", max_length=80)
    style_key: str = Field(default="guardrisk_orange", max_length=80)
    html_content: str = Field(default="<p></p>", max_length=500_000)
    plain_text: str = Field(default="", max_length=250_000)
    settings: dict = Field(default_factory=dict)
    visibility: str = Field(default="private", pattern="^(private|team)$")


class StudioUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    style_key: str | None = Field(default=None, max_length=80)
    html_content: str | None = Field(default=None, max_length=500_000)
    plain_text: str | None = Field(default=None, max_length=250_000)
    settings: dict | None = None
    visibility: str | None = Field(default=None, pattern="^(private|team)$")
    status: str | None = Field(default=None, pattern="^(draft|review|final|archived)$")
    expected_version: int | None = Field(default=None, ge=1)


class CollaboratorCreate(BaseModel):
    user_id: uuid.UUID
    permission: str = Field(default="view", pattern="^(view|edit)$")


def _serialize(document: StudioDocument, *, can_edit: bool = True) -> dict:
    return {
        "id": str(document.id),
        "owner_user_id": str(document.owner_user_id),
        "title": document.title,
        "template_key": document.template_key,
        "style_key": document.style_key,
        "status": document.status,
        "visibility": document.visibility,
        "html_content": document.html_content,
        "plain_text": document.plain_text,
        "settings": document.settings,
        "version": document.version,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
        "can_edit": can_edit,
    }


async def _access(
    session: DbSession,
    user: User,
    document_id: uuid.UUID,
    *,
    write: bool = False,
) -> tuple[StudioDocument, bool]:
    document = await session.get(StudioDocument, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if user.is_superuser or document.owner_user_id == user.id:
        return document, True
    collaboration = (
        await session.execute(
            select(StudioCollaborator).where(
                StudioCollaborator.document_id == document_id,
                StudioCollaborator.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if collaboration:
        can_edit = collaboration.permission == "edit"
        if write and not can_edit:
            raise HTTPException(
                status_code=403,
                detail="This document was shared with view-only access",
            )
        return document, can_edit
    if document.visibility == "team" and not write:
        return document, False
    raise HTTPException(status_code=403, detail="You do not have access to this document")


@router.get("")
async def list_documents(
    session: DbSession,
    user: CurrentUser,
    q: str = "",
    document_status: str = "",
) -> list[dict]:
    collaborator_ids = select(StudioCollaborator.document_id).where(
        StudioCollaborator.user_id == user.id
    )
    access_filter = or_(
        StudioDocument.owner_user_id == user.id,
        StudioDocument.visibility == "team",
        StudioDocument.id.in_(collaborator_ids),
    )
    conditions = [access_filter]
    if q.strip():
        token = f"%{q.strip()}%"
        conditions.append(
            or_(StudioDocument.title.ilike(token), StudioDocument.plain_text.ilike(token))
        )
    if document_status.strip():
        conditions.append(StudioDocument.status == document_status.strip())
    rows = (
        await session.execute(
            select(StudioDocument)
            .where(and_(*conditions))
            .order_by(StudioDocument.updated_at.desc())
            .limit(300)
        )
    ).scalars().all()
    result: list[dict] = []
    for row in rows:
        can_edit = user.is_superuser or row.owner_user_id == user.id
        if not can_edit:
            collaboration = (
                await session.execute(
                    select(StudioCollaborator.permission).where(
                        StudioCollaborator.document_id == row.id,
                        StudioCollaborator.user_id == user.id,
                    )
                )
            ).scalar_one_or_none()
            can_edit = collaboration == "edit"
        result.append(_serialize(row, can_edit=can_edit))
    return result


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_document(
    payload: StudioCreate,
    request: Request,
    session: DbSession,
    user: CurrentUser,
) -> dict:
    document = StudioDocument(
        owner_user_id=user.id,
        title=payload.title.strip(),
        template_key=payload.template_key,
        style_key=payload.style_key,
        html_content=payload.html_content,
        plain_text=payload.plain_text,
        settings=payload.settings,
        visibility=payload.visibility,
    )
    session.add(document)
    await session.flush()
    await record_audit_event(
        session,
        action="document_studio.created",
        entity_type="studio_document",
        entity_id=str(document.id),
        actor_user_id=user.id,
        details={"template_key": document.template_key, "title": document.title},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    await session.refresh(document)
    return _serialize(document)


@router.get("/{document_id}")
async def get_document(
    document_id: uuid.UUID,
    session: DbSession,
    user: CurrentUser,
) -> dict:
    document, can_edit = await _access(session, user, document_id)
    return _serialize(document, can_edit=can_edit)


@router.patch("/{document_id}")
async def update_document(
    document_id: uuid.UUID,
    payload: StudioUpdate,
    request: Request,
    session: DbSession,
    user: CurrentUser,
) -> dict:
    document, _ = await _access(session, user, document_id, write=True)
    if payload.expected_version is not None and payload.expected_version != document.version:
        raise HTTPException(
            status_code=409,
            detail="This document changed elsewhere. Reload before saving again.",
        )
    for field in (
        "title",
        "style_key",
        "html_content",
        "plain_text",
        "settings",
        "visibility",
        "status",
    ):
        value = getattr(payload, field)
        if value is not None:
            if field == "title":
                value = value.strip()
            setattr(document, field, value)
    document.version += 1
    await record_audit_event(
        session,
        action="document_studio.saved",
        entity_type="studio_document",
        entity_id=str(document.id),
        actor_user_id=user.id,
        details={"version": document.version},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    await session.refresh(document)
    return _serialize(document)


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    request: Request,
    session: DbSession,
    user: CurrentUser,
) -> Response:
    document, _ = await _access(session, user, document_id, write=True)
    if not user.is_superuser and document.owner_user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the document owner can delete it")
    await record_audit_event(
        session,
        action="document_studio.deleted",
        entity_type="studio_document",
        entity_id=str(document.id),
        actor_user_id=user.id,
        details={"title": document.title},
        ip_address=request.client.host if request.client else None,
    )
    await session.delete(document)
    await session.commit()
    return Response(status_code=204)


@router.post("/{document_id}/revisions", status_code=201)
async def checkpoint(
    document_id: uuid.UUID,
    session: DbSession,
    user: CurrentUser,
) -> dict:
    document, _ = await _access(session, user, document_id, write=True)
    revision = StudioRevision(
        document_id=document.id,
        version=document.version,
        title=document.title,
        html_content=document.html_content,
        plain_text=document.plain_text,
        settings=document.settings,
        saved_by_user_id=user.id,
    )
    session.add(revision)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        existing = (
            await session.execute(
                select(StudioRevision).where(
                    StudioRevision.document_id == document.id,
                    StudioRevision.version == document.version,
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            raise
        revision = existing
    return {
        "id": str(revision.id),
        "version": revision.version,
        "title": revision.title,
        "created_at": revision.created_at,
    }


@router.get("/{document_id}/revisions")
async def revisions(
    document_id: uuid.UUID,
    session: DbSession,
    user: CurrentUser,
) -> list[dict]:
    await _access(session, user, document_id)
    rows = (
        await session.execute(
            select(StudioRevision)
            .where(StudioRevision.document_id == document_id)
            .order_by(StudioRevision.version.desc())
        )
    ).scalars().all()
    return [
        {
            "id": str(row.id),
            "version": row.version,
            "title": row.title,
            "html_content": row.html_content,
            "plain_text": row.plain_text,
            "settings": row.settings,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.get("/{document_id}/collaborators")
async def collaborators(
    document_id: uuid.UUID,
    session: DbSession,
    user: CurrentUser,
) -> list[dict]:
    document, _ = await _access(session, user, document_id)
    if not user.is_superuser and document.owner_user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the owner can manage sharing")
    rows = (
        await session.execute(
            select(StudioCollaborator, User)
            .join(User, User.id == StudioCollaborator.user_id)
            .where(StudioCollaborator.document_id == document_id)
            .order_by(User.full_name)
        )
    ).all()
    return [
        {
            "user_id": str(collab.user_id),
            "name": target.full_name,
            "email": target.email,
            "permission": collab.permission,
        }
        for collab, target in rows
    ]


@router.post("/{document_id}/collaborators", status_code=201)
async def add_collaborator(
    document_id: uuid.UUID,
    payload: CollaboratorCreate,
    session: DbSession,
    user: CurrentUser,
) -> dict:
    document, _ = await _access(session, user, document_id)
    if not user.is_superuser and document.owner_user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the owner can manage sharing")
    if payload.user_id == document.owner_user_id:
        raise HTTPException(status_code=400, detail="The owner already has full access")
    target = await session.get(User, payload.user_id)
    if target is None or not target.is_active:
        raise HTTPException(status_code=404, detail="User not found")
    existing = (
        await session.execute(
            select(StudioCollaborator).where(
                StudioCollaborator.document_id == document_id,
                StudioCollaborator.user_id == payload.user_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        existing.permission = payload.permission
        collaboration = existing
    else:
        collaboration = StudioCollaborator(
            document_id=document_id,
            user_id=payload.user_id,
            permission=payload.permission,
        )
        session.add(collaboration)
    await session.commit()
    return {
        "user_id": str(target.id),
        "name": target.full_name,
        "email": target.email,
        "permission": collaboration.permission,
    }


@router.delete("/{document_id}/collaborators/{target_user_id}", status_code=204)
async def remove_collaborator(
    document_id: uuid.UUID,
    target_user_id: uuid.UUID,
    session: DbSession,
    user: CurrentUser,
) -> Response:
    document, _ = await _access(session, user, document_id)
    if not user.is_superuser and document.owner_user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the owner can manage sharing")
    await session.execute(
        delete(StudioCollaborator).where(
            StudioCollaborator.document_id == document_id,
            StudioCollaborator.user_id == target_user_id,
        )
    )
    await session.commit()
    return Response(status_code=204)


def _clean_html_for_reportlab(html: str) -> list[str]:
    text = html
    text = re.sub(r"<\s*br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(
        r"</\s*(p|div|h[1-6]|li|tr)\s*>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"<\s*li[^>]*>", "• ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text).replace("\xa0", " ")
    return [line.strip() for line in text.splitlines() if line.strip()]


def _pdf_for(document: StudioDocument) -> BytesIO:
    settings = document.settings or {}
    page_size = LETTER if settings.get("page_size") == "letter" else A4
    if settings.get("orientation") == "landscape":
        page_size = landscape(page_size)
    margin_mm = max(10, min(40, int(settings.get("margin_mm", 20) or 20)))
    buffer = BytesIO()
    pdf = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        rightMargin=margin_mm * mm,
        leftMargin=margin_mm * mm,
        topMargin=margin_mm * mm,
        bottomMargin=margin_mm * mm,
        title=document.title,
        author="gRisk Document Studio",
    )
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "gRiskBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=15,
        textColor=colors.HexColor("#25272B"),
        spaceAfter=7,
    )
    story = []
    if settings.get("brand_header", True):
        story.extend(
            [
                Paragraph(
                    '<font color="#F47A20"><b>G</b></font>  <b>GUARDRISK</b>',
                    styles["Title"],
                ),
                Paragraph(
                    "Insurance · Medical Aid · Bonds & Guarantees · Risk Management",
                    styles["Normal"],
                ),
                Spacer(1, 5 * mm),
            ]
        )
    for line in _clean_html_for_reportlab(document.html_content):
        if line == "[[PAGE_BREAK]]":
            story.append(PageBreak())
        else:
            story.append(Paragraph(line.replace("&", "&amp;"), body))
    pdf.build(story)
    buffer.seek(0)
    return buffer


@router.get("/{document_id}/export/pdf")
async def export_pdf(
    document_id: uuid.UUID,
    session: DbSession,
    user: CurrentUser,
) -> StreamingResponse:
    document, _ = await _access(session, user, document_id)
    safe = (
        re.sub(r"[^A-Za-z0-9_-]+", "_", document.title).strip("_")
        or "guardrisk-document"
    )
    return StreamingResponse(
        _pdf_for(document),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe}.pdf"'},
    )


@router.get("/{document_id}/export/word")
async def export_word(
    document_id: uuid.UUID,
    session: DbSession,
    user: CurrentUser,
) -> Response:
    document, _ = await _access(session, user, document_id)
    safe = (
        re.sub(r"[^A-Za-z0-9_-]+", "_", document.title).strip("_")
        or "guardrisk-document"
    )
    html = (
        '<!doctype html><html><head><meta charset="utf-8"><title>'
        f"{document.title}</title></head><body>{document.html_content}</body></html>"
    )
    return Response(
        content=html,
        media_type="application/msword",
        headers={"Content-Disposition": f'attachment; filename="{safe}.doc"'},
    )
