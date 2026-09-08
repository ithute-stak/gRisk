"""add persistent document studio workspace

Revision ID: 20260908_0013
Revises: 20260908_0012
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260908_0013"
down_revision: str | None = "20260908_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "studio_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("template_key", sa.String(length=80), server_default="blank", nullable=False),
        sa.Column("style_key", sa.String(length=80), server_default="guardrisk_orange", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("visibility", sa.String(length=32), server_default="private", nullable=False),
        sa.Column("html_content", sa.Text(), server_default="<p></p>", nullable=False),
        sa.Column("plain_text", sa.Text(), server_default="", nullable=False),
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("owner_user_id", "template_key", "status", "visibility", "created_at", "updated_at"):
        op.create_index(f"ix_studio_documents_{column}", "studio_documents", [column])

    op.create_table(
        "studio_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("html_content", sa.Text(), nullable=False),
        sa.Column("plain_text", sa.Text(), server_default="", nullable=False),
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("saved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["studio_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["saved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "version", name="uq_studio_revision_document_version"),
    )
    op.create_index("ix_studio_revisions_document_id", "studio_revisions", ["document_id"])
    op.create_index("ix_studio_revisions_saved_by_user_id", "studio_revisions", ["saved_by_user_id"])
    op.create_index("ix_studio_revisions_created_at", "studio_revisions", ["created_at"])

    op.create_table(
        "studio_collaborators",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permission", sa.String(length=16), server_default="view", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["studio_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "user_id", name="uq_studio_collaborator_document_user"),
    )
    op.create_index("ix_studio_collaborators_document_id", "studio_collaborators", ["document_id"])
    op.create_index("ix_studio_collaborators_user_id", "studio_collaborators", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_studio_collaborators_user_id", table_name="studio_collaborators")
    op.drop_index("ix_studio_collaborators_document_id", table_name="studio_collaborators")
    op.drop_table("studio_collaborators")
    op.drop_index("ix_studio_revisions_created_at", table_name="studio_revisions")
    op.drop_index("ix_studio_revisions_saved_by_user_id", table_name="studio_revisions")
    op.drop_index("ix_studio_revisions_document_id", table_name="studio_revisions")
    op.drop_table("studio_revisions")
    for column in reversed(("owner_user_id", "template_key", "status", "visibility", "created_at", "updated_at")):
        op.drop_index(f"ix_studio_documents_{column}", table_name="studio_documents")
    op.drop_table("studio_documents")
