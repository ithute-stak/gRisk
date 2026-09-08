"""create bonds guarantees and risk management tables

Revision ID: 20260908_0010
Revises: 20260908_0009
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260908_0010"
down_revision: str | None = "20260908_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "guarantees",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("guarantee_number", sa.String(length=48), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("guarantee_type", sa.String(length=60), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("beneficiary", sa.String(length=200), nullable=False),
        sa.Column("principal", sa.String(length=200), nullable=True),
        sa.Column("tender_reference", sa.String(length=120), nullable=True),
        sa.Column("contract_reference", sa.String(length=120), nullable=True),
        sa.Column("contract_description", sa.Text(), nullable=True),
        sa.Column("currency", sa.String(length=3), server_default="LSL", nullable=False),
        sa.Column("contract_value", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("guarantee_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("issuer_name", sa.String(length=200), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("assigned_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_guarantees_guarantee_number", "guarantees", ["guarantee_number"], unique=True)
    op.create_index("ix_guarantees_customer_id", "guarantees", ["customer_id"], unique=False)
    op.create_index("ix_guarantees_guarantee_type", "guarantees", ["guarantee_type"], unique=False)
    op.create_index("ix_guarantees_status", "guarantees", ["status"], unique=False)
    op.create_index("ix_guarantees_tender_reference", "guarantees", ["tender_reference"], unique=False)
    op.create_index("ix_guarantees_contract_reference", "guarantees", ["contract_reference"], unique=False)
    op.create_index("ix_guarantees_expiry_date", "guarantees", ["expiry_date"], unique=False)
    op.create_index("ix_guarantees_assigned_user_id", "guarantees", ["assigned_user_id"], unique=False)
    op.create_index("ix_guarantees_created_by_user_id", "guarantees", ["created_by_user_id"], unique=False)

    op.create_table(
        "guarantee_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("guarantee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("from_status", sa.String(length=30), nullable=True),
        sa.Column("to_status", sa.String(length=30), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["guarantee_id"], ["guarantees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_guarantee_events_guarantee_id", "guarantee_events", ["guarantee_id"], unique=False)
    op.create_index("ix_guarantee_events_event_type", "guarantee_events", ["event_type"], unique=False)
    op.create_index("ix_guarantee_events_actor_user_id", "guarantee_events", ["actor_user_id"], unique=False)

    op.create_table(
        "risk_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assessment_number", sa.String(length=48), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assessment_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("assessment_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("overall_level", sa.String(length=20), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("recommendations", sa.Text(), nullable=True),
        sa.Column("assigned_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_risk_assessments_assessment_number", "risk_assessments", ["assessment_number"], unique=True)
    op.create_index("ix_risk_assessments_customer_id", "risk_assessments", ["customer_id"], unique=False)
    op.create_index("ix_risk_assessments_assessment_type", "risk_assessments", ["assessment_type"], unique=False)
    op.create_index("ix_risk_assessments_assessment_date", "risk_assessments", ["assessment_date"], unique=False)
    op.create_index("ix_risk_assessments_status", "risk_assessments", ["status"], unique=False)
    op.create_index("ix_risk_assessments_overall_level", "risk_assessments", ["overall_level"], unique=False)
    op.create_index("ix_risk_assessments_assigned_user_id", "risk_assessments", ["assigned_user_id"], unique=False)
    op.create_index("ix_risk_assessments_created_by_user_id", "risk_assessments", ["created_by_user_id"], unique=False)

    op.create_table(
        "risk_register_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("likelihood", sa.Integer(), nullable=False),
        sa.Column("impact", sa.Integer(), nullable=False),
        sa.Column("inherent_score", sa.Integer(), nullable=False),
        sa.Column("inherent_level", sa.String(length=20), nullable=False),
        sa.Column("existing_controls", sa.Text(), nullable=True),
        sa.Column("treatment_plan", sa.Text(), nullable=True),
        sa.Column("risk_owner", sa.String(length=160), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="open", nullable=False),
        sa.Column("residual_likelihood", sa.Integer(), nullable=True),
        sa.Column("residual_impact", sa.Integer(), nullable=True),
        sa.Column("residual_score", sa.Integer(), nullable=True),
        sa.Column("residual_level", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["assessment_id"], ["risk_assessments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_risk_register_items_assessment_id", "risk_register_items", ["assessment_id"], unique=False)
    op.create_index("ix_risk_register_items_category", "risk_register_items", ["category"], unique=False)
    op.create_index("ix_risk_register_items_inherent_score", "risk_register_items", ["inherent_score"], unique=False)
    op.create_index("ix_risk_register_items_inherent_level", "risk_register_items", ["inherent_level"], unique=False)
    op.create_index("ix_risk_register_items_due_date", "risk_register_items", ["due_date"], unique=False)
    op.create_index("ix_risk_register_items_status", "risk_register_items", ["status"], unique=False)
    op.create_index("ix_risk_register_items_residual_score", "risk_register_items", ["residual_score"], unique=False)
    op.create_index("ix_risk_register_items_residual_level", "risk_register_items", ["residual_level"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_risk_register_items_residual_level", table_name="risk_register_items")
    op.drop_index("ix_risk_register_items_residual_score", table_name="risk_register_items")
    op.drop_index("ix_risk_register_items_status", table_name="risk_register_items")
    op.drop_index("ix_risk_register_items_due_date", table_name="risk_register_items")
    op.drop_index("ix_risk_register_items_inherent_level", table_name="risk_register_items")
    op.drop_index("ix_risk_register_items_inherent_score", table_name="risk_register_items")
    op.drop_index("ix_risk_register_items_category", table_name="risk_register_items")
    op.drop_index("ix_risk_register_items_assessment_id", table_name="risk_register_items")
    op.drop_table("risk_register_items")

    op.drop_index("ix_risk_assessments_created_by_user_id", table_name="risk_assessments")
    op.drop_index("ix_risk_assessments_assigned_user_id", table_name="risk_assessments")
    op.drop_index("ix_risk_assessments_overall_level", table_name="risk_assessments")
    op.drop_index("ix_risk_assessments_status", table_name="risk_assessments")
    op.drop_index("ix_risk_assessments_assessment_date", table_name="risk_assessments")
    op.drop_index("ix_risk_assessments_assessment_type", table_name="risk_assessments")
    op.drop_index("ix_risk_assessments_customer_id", table_name="risk_assessments")
    op.drop_index("ix_risk_assessments_assessment_number", table_name="risk_assessments")
    op.drop_table("risk_assessments")

    op.drop_index("ix_guarantee_events_actor_user_id", table_name="guarantee_events")
    op.drop_index("ix_guarantee_events_event_type", table_name="guarantee_events")
    op.drop_index("ix_guarantee_events_guarantee_id", table_name="guarantee_events")
    op.drop_table("guarantee_events")

    op.drop_index("ix_guarantees_created_by_user_id", table_name="guarantees")
    op.drop_index("ix_guarantees_assigned_user_id", table_name="guarantees")
    op.drop_index("ix_guarantees_expiry_date", table_name="guarantees")
    op.drop_index("ix_guarantees_contract_reference", table_name="guarantees")
    op.drop_index("ix_guarantees_tender_reference", table_name="guarantees")
    op.drop_index("ix_guarantees_status", table_name="guarantees")
    op.drop_index("ix_guarantees_guarantee_type", table_name="guarantees")
    op.drop_index("ix_guarantees_customer_id", table_name="guarantees")
    op.drop_index("ix_guarantees_guarantee_number", table_name="guarantees")
    op.drop_table("guarantees")
