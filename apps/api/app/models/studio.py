import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StudioDocument(Base):
    __tablename__ = "studio_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(240), default="Untitled document")
    template_key: Mapped[str] = mapped_column(String(80), default="blank", server_default="blank", index=True)
    style_key: Mapped[str] = mapped_column(String(80), default="guardrisk_orange", server_default="guardrisk_orange")
    status: Mapped[str] = mapped_column(String(32), default="draft", server_default="draft", index=True)
    visibility: Mapped[str] = mapped_column(String(32), default="private", server_default="private", index=True)
    html_content: Mapped[str] = mapped_column(Text, default="<p></p>", server_default="<p></p>")
    plain_text: Mapped[str] = mapped_column(Text, default="", server_default="")
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True
    )


class StudioRevision(Base):
    __tablename__ = "studio_revisions"
    __table_args__ = (UniqueConstraint("document_id", "version", name="uq_studio_revision_document_version"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("studio_documents.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(240))
    html_content: Mapped[str] = mapped_column(Text)
    plain_text: Mapped[str] = mapped_column(Text, default="", server_default="")
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    saved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class StudioCollaborator(Base):
    __tablename__ = "studio_collaborators"
    __table_args__ = (UniqueConstraint("document_id", "user_id", name="uq_studio_collaborator_document_user"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("studio_documents.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    permission: Mapped[str] = mapped_column(String(16), default="view", server_default="view")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
