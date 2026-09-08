"""insurance products quotations and policies

Revision ID: 20260907_0003
Revises: 20260907_0002
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260907_0003"
down_revision: str | None = "20260907_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "insurance_products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_insurance_products_code", "insurance_products", ["code"], unique=True)
    op.create_index("ix_insurance_products_name", "insurance_products", ["name"], unique=False)
    op.create_index("ix_insurance_products_category", "insurance_products", ["category"], unique=False)
    op.create_index("ix_insurance_products_is_active", "insurance_products", ["is_active"], unique=False)

    op.create_table(
        "quotes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quote_number", sa.String(length=40), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="LSL", nullable=False),
        sa.Column("sum_insured", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("premium", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("third_party_limit", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["insurance_products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("quote_number"),
    )
    op.create_index("ix_quotes_quote_number", "quotes", ["quote_number"], unique=True)
    op.create_index("ix_quotes_customer_id", "quotes", ["customer_id"], unique=False)
    op.create_index("ix_quotes_product_id", "quotes", ["product_id"], unique=False)
    op.create_index("ix_quotes_status", "quotes", ["status"], unique=False)
    op.create_index("ix_quotes_created_by_user_id", "quotes", ["created_by_user_id"], unique=False)

    op.create_table(
        "quote_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["quote_id"], ["quotes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quote_items_quote_id", "quote_items", ["quote_id"], unique=False)

    op.create_table(
        "policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_number", sa.String(length=40), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_quote_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="active", nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="LSL", nullable=False),
        sa.Column("sum_insured", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("premium", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["insurance_products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_quote_id"], ["quotes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("policy_number"),
        sa.UniqueConstraint("source_quote_id"),
    )
    op.create_index("ix_policies_policy_number", "policies", ["policy_number"], unique=True)
    op.create_index("ix_policies_customer_id", "policies", ["customer_id"], unique=False)
    op.create_index("ix_policies_product_id", "policies", ["product_id"], unique=False)
    op.create_index("ix_policies_status", "policies", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_policies_status", table_name="policies")
    op.drop_index("ix_policies_product_id", table_name="policies")
    op.drop_index("ix_policies_customer_id", table_name="policies")
    op.drop_index("ix_policies_policy_number", table_name="policies")
    op.drop_table("policies")

    op.drop_index("ix_quote_items_quote_id", table_name="quote_items")
    op.drop_table("quote_items")

    op.drop_index("ix_quotes_created_by_user_id", table_name="quotes")
    op.drop_index("ix_quotes_status", table_name="quotes")
    op.drop_index("ix_quotes_product_id", table_name="quotes")
    op.drop_index("ix_quotes_customer_id", table_name="quotes")
    op.drop_index("ix_quotes_quote_number", table_name="quotes")
    op.drop_table("quotes")

    op.drop_index("ix_insurance_products_is_active", table_name="insurance_products")
    op.drop_index("ix_insurance_products_category", table_name="insurance_products")
    op.drop_index("ix_insurance_products_name", table_name="insurance_products")
    op.drop_index("ix_insurance_products_code", table_name="insurance_products")
    op.drop_table("insurance_products")
