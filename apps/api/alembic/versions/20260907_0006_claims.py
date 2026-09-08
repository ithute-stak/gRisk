"""create claims and claim event tables

Revision ID: 20260907_0006
Revises: 20260907_0005
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260907_0006"
down_revision: str | None = "20260907_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claim_number", sa.String(length=48), nullable=False),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claim_type", sa.String(length=60), server_default="general", nullable=False),
        sa.Column("incident_date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("claim_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("approved_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="reported", nullable=False),
        sa.Column("priority", sa.String(length=20), server_default="normal", nullable=False),
        sa.Column("assigned_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reported_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["policy_id"], ["policies.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_claims_claim_number"), "claims", ["claim_number"], unique=True)
    op.create_index(op.f("ix_claims_policy_id"), "claims", ["policy_id"], unique=False)
    op.create_index(op.f("ix_claims_customer_id"), "claims", ["customer_id"], unique=False)
    op.create_index(op.f("ix_claims_claim_type"), "claims", ["claim_type"], unique=False)
    op.create_index(op.f("ix_claims_incident_date"), "claims", ["incident_date"], unique=False)
    op.create_index(op.f("ix_claims_status"), "claims", ["status"], unique=False)
    op.create_index(op.f("ix_claims_priority"), "claims", ["priority"], unique=False)
    op.create_index(op.f("ix_claims_assigned_user_id"), "claims", ["assigned_user_id"], unique=False)
    op.create_index(op.f("ix_claims_created_by_user_id"), "claims", ["created_by_user_id"], unique=False)

    op.create_table(
        "claim_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("from_status", sa.String(length=30), nullable=True),
        sa.Column("to_status", sa.String(length=30), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_claim_events_claim_id"), "claim_events", ["claim_id"], unique=False)
    op.create_index(op.f("ix_claim_events_event_type"), "claim_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_claim_events_actor_user_id"), "claim_events", ["actor_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_claim_events_actor_user_id"), table_name="claim_events")
    op.drop_index(op.f("ix_claim_events_event_type"), table_name="claim_events")
    op.drop_index(op.f("ix_claim_events_claim_id"), table_name="claim_events")
    op.drop_table("claim_events")

    op.drop_index(op.f("ix_claims_created_by_user_id"), table_name="claims")
    op.drop_index(op.f("ix_claims_assigned_user_id"), table_name="claims")
    op.drop_index(op.f("ix_claims_priority"), table_name="claims")
    op.drop_index(op.f("ix_claims_status"), table_name="claims")
    op.drop_index(op.f("ix_claims_incident_date"), table_name="claims")
    op.drop_index(op.f("ix_claims_claim_type"), table_name="claims")
    op.drop_index(op.f("ix_claims_customer_id"), table_name="claims")
    op.drop_index(op.f("ix_claims_policy_id"), table_name="claims")
    op.drop_index(op.f("ix_claims_claim_number"), table_name="claims")
    op.drop_table("claims")
