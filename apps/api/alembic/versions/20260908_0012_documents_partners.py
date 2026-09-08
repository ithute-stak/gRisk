"""create document and strategic partner tables

Revision ID: 20260908_0012
Revises: 20260908_0011
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260908_0012"
down_revision: str | None = "20260908_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entity_type", sa.String(length=64), server_default="customer", nullable=False),
        sa.Column("entity_id", sa.String(length=100), nullable=True),
        sa.Column("category", sa.String(length=64), server_default="general", nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=160), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=24), server_default="active", nullable=False),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_customer_id", "documents", ["customer_id"], unique=False)
    op.create_index("ix_documents_entity_type", "documents", ["entity_type"], unique=False)
    op.create_index("ix_documents_entity_id", "documents", ["entity_id"], unique=False)
    op.create_index("ix_documents_category", "documents", ["category"], unique=False)
    op.create_index("ix_documents_storage_key", "documents", ["storage_key"], unique=True)
    op.create_index("ix_documents_status", "documents", ["status"], unique=False)
    op.create_index("ix_documents_uploaded_by_user_id", "documents", ["uploaded_by_user_id"], unique=False)
    op.create_index("ix_documents_created_at", "documents", ["created_at"], unique=False)

    op.create_table(
        "partners",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_number", sa.String(length=40), nullable=False),
        sa.Column("partner_type", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("external_reference", sa.String(length=160), nullable=True),
        sa.Column("integration_status", sa.String(length=40), server_default="not_configured", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_partners_partner_number", "partners", ["partner_number"], unique=True)
    op.create_index("ix_partners_partner_type", "partners", ["partner_type"], unique=False)
    op.create_index("ix_partners_name", "partners", ["name"], unique=False)
    op.create_index("ix_partners_external_reference", "partners", ["external_reference"], unique=False)
    op.create_index("ix_partners_integration_status", "partners", ["integration_status"], unique=False)
    op.create_index("ix_partners_is_active", "partners", ["is_active"], unique=False)
    op.create_index("ix_partners_created_at", "partners", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_partners_created_at", table_name="partners")
    op.drop_index("ix_partners_is_active", table_name="partners")
    op.drop_index("ix_partners_integration_status", table_name="partners")
    op.drop_index("ix_partners_external_reference", table_name="partners")
    op.drop_index("ix_partners_name", table_name="partners")
    op.drop_index("ix_partners_partner_type", table_name="partners")
    op.drop_index("ix_partners_partner_number", table_name="partners")
    op.drop_table("partners")

    op.drop_index("ix_documents_created_at", table_name="documents")
    op.drop_index("ix_documents_uploaded_by_user_id", table_name="documents")
    op.drop_index("ix_documents_status", table_name="documents")
    op.drop_index("ix_documents_storage_key", table_name="documents")
    op.drop_index("ix_documents_category", table_name="documents")
    op.drop_index("ix_documents_entity_id", table_name="documents")
    op.drop_index("ix_documents_entity_type", table_name="documents")
    op.drop_index("ix_documents_customer_id", table_name="documents")
    op.drop_table("documents")
