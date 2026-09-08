"""create finance notifications and customer portal tables

Revision ID: 20260908_0011
Revises: 20260908_0010
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260908_0011"
down_revision: str | None = "20260908_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_number", sa.String(length=48), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("medical_member_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("invoice_type", sa.String(length=50), server_default="premium", nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="LSL", nullable=False),
        sa.Column("amount_due", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("amount_paid", sa.Numeric(precision=18, scale=2), server_default="0", nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["policy_id"], ["policies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["medical_member_id"], ["medical_members.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoices_invoice_number", "invoices", ["invoice_number"], unique=True)
    op.create_index("ix_invoices_customer_id", "invoices", ["customer_id"], unique=False)
    op.create_index("ix_invoices_policy_id", "invoices", ["policy_id"], unique=False)
    op.create_index("ix_invoices_medical_member_id", "invoices", ["medical_member_id"], unique=False)
    op.create_index("ix_invoices_status", "invoices", ["status"], unique=False)
    op.create_index("ix_invoices_invoice_type", "invoices", ["invoice_type"], unique=False)
    op.create_index("ix_invoices_issue_date", "invoices", ["issue_date"], unique=False)
    op.create_index("ix_invoices_due_date", "invoices", ["due_date"], unique=False)
    op.create_index("ix_invoices_created_by_user_id", "invoices", ["created_by_user_id"], unique=False)

    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_number", sa.String(length=48), nullable=False),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="LSL", nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("payment_method", sa.String(length=50), nullable=False),
        sa.Column("reference", sa.String(length=160), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("received_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["received_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payments_payment_number", "payments", ["payment_number"], unique=True)
    op.create_index("ix_payments_invoice_id", "payments", ["invoice_id"], unique=False)
    op.create_index("ix_payments_customer_id", "payments", ["customer_id"], unique=False)
    op.create_index("ix_payments_payment_date", "payments", ["payment_date"], unique=False)
    op.create_index("ix_payments_payment_method", "payments", ["payment_method"], unique=False)
    op.create_index("ix_payments_reference", "payments", ["reference"], unique=False)
    op.create_index("ix_payments_received_by_user_id", "payments", ["received_by_user_id"], unique=False)

    op.create_table(
        "customer_portal_access",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portal_role", sa.String(length=30), server_default="member", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "customer_id", name="uq_customer_portal_user_customer"),
    )
    op.create_index("ix_customer_portal_access_user_id", "customer_portal_access", ["user_id"], unique=False)
    op.create_index("ix_customer_portal_access_customer_id", "customer_portal_access", ["customer_id"], unique=False)
    op.create_index("ix_customer_portal_access_portal_role", "customer_portal_access", ["portal_role"], unique=False)
    op.create_index("ix_customer_portal_access_is_active", "customer_portal_access", ["is_active"], unique=False)
    op.create_index("ix_customer_portal_access_created_by_user_id", "customer_portal_access", ["created_by_user_id"], unique=False)

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("category", sa.String(length=50), server_default="general", nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="unread", nullable=False),
        sa.Column("action_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"], unique=False)
    op.create_index("ix_notifications_customer_id", "notifications", ["customer_id"], unique=False)
    op.create_index("ix_notifications_category", "notifications", ["category"], unique=False)
    op.create_index("ix_notifications_status", "notifications", ["status"], unique=False)
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_status", table_name="notifications")
    op.drop_index("ix_notifications_category", table_name="notifications")
    op.drop_index("ix_notifications_customer_id", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("ix_customer_portal_access_created_by_user_id", table_name="customer_portal_access")
    op.drop_index("ix_customer_portal_access_is_active", table_name="customer_portal_access")
    op.drop_index("ix_customer_portal_access_portal_role", table_name="customer_portal_access")
    op.drop_index("ix_customer_portal_access_customer_id", table_name="customer_portal_access")
    op.drop_index("ix_customer_portal_access_user_id", table_name="customer_portal_access")
    op.drop_table("customer_portal_access")

    op.drop_index("ix_payments_received_by_user_id", table_name="payments")
    op.drop_index("ix_payments_reference", table_name="payments")
    op.drop_index("ix_payments_payment_method", table_name="payments")
    op.drop_index("ix_payments_payment_date", table_name="payments")
    op.drop_index("ix_payments_customer_id", table_name="payments")
    op.drop_index("ix_payments_invoice_id", table_name="payments")
    op.drop_index("ix_payments_payment_number", table_name="payments")
    op.drop_table("payments")

    op.drop_index("ix_invoices_created_by_user_id", table_name="invoices")
    op.drop_index("ix_invoices_due_date", table_name="invoices")
    op.drop_index("ix_invoices_issue_date", table_name="invoices")
    op.drop_index("ix_invoices_invoice_type", table_name="invoices")
    op.drop_index("ix_invoices_status", table_name="invoices")
    op.drop_index("ix_invoices_medical_member_id", table_name="invoices")
    op.drop_index("ix_invoices_policy_id", table_name="invoices")
    op.drop_index("ix_invoices_customer_id", table_name="invoices")
    op.drop_index("ix_invoices_invoice_number", table_name="invoices")
    op.drop_table("invoices")
