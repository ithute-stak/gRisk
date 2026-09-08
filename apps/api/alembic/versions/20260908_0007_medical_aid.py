"""create medical aid administration tables

Revision ID: 20260908_0007
Revises: 20260907_0006
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260908_0007"
down_revision: str | None = "20260907_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "medical_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("monthly_premium", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), server_default="LSL", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_medical_plans_code", "medical_plans", ["code"], unique=True)
    op.create_index("ix_medical_plans_name", "medical_plans", ["name"], unique=False)
    op.create_index("ix_medical_plans_is_active", "medical_plans", ["is_active"], unique=False)

    op.create_table(
        "medical_benefits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("annual_monetary_limit", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("per_event_limit", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("annual_visit_limit", sa.Integer(), nullable=True),
        sa.Column("requires_authorisation", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["medical_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plan_id", "code", name="uq_medical_benefit_plan_code"),
    )
    op.create_index("ix_medical_benefits_plan_id", "medical_benefits", ["plan_id"], unique=False)
    op.create_index("ix_medical_benefits_code", "medical_benefits", ["code"], unique=False)
    op.create_index("ix_medical_benefits_category", "medical_benefits", ["category"], unique=False)
    op.create_index("ix_medical_benefits_is_active", "medical_benefits", ["is_active"], unique=False)

    op.create_table(
        "medical_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_number", sa.String(length=48), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="active", nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["plan_id"], ["medical_plans.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("member_number"),
    )
    op.create_index("ix_medical_members_member_number", "medical_members", ["member_number"], unique=True)
    op.create_index("ix_medical_members_customer_id", "medical_members", ["customer_id"], unique=False)
    op.create_index("ix_medical_members_plan_id", "medical_members", ["plan_id"], unique=False)
    op.create_index("ix_medical_members_status", "medical_members", ["status"], unique=False)
    op.create_index("ix_medical_members_created_by_user_id", "medical_members", ["created_by_user_id"], unique=False)

    op.create_table(
        "medical_dependants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("relationship_type", sa.String(length=50), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["member_id"], ["medical_members.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_medical_dependants_member_id", "medical_dependants", ["member_id"], unique=False)
    op.create_index("ix_medical_dependants_relationship_type", "medical_dependants", ["relationship_type"], unique=False)
    op.create_index("ix_medical_dependants_status", "medical_dependants", ["status"], unique=False)

    op.create_table(
        "medical_utilisations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("benefit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dependant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("units", sa.Integer(), server_default="1", nullable=False),
        sa.Column("provider_name", sa.String(length=200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["member_id"], ["medical_members.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["benefit_id"], ["medical_benefits.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["dependant_id"], ["medical_dependants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_medical_utilisations_member_id", "medical_utilisations", ["member_id"], unique=False)
    op.create_index("ix_medical_utilisations_benefit_id", "medical_utilisations", ["benefit_id"], unique=False)
    op.create_index("ix_medical_utilisations_dependant_id", "medical_utilisations", ["dependant_id"], unique=False)
    op.create_index("ix_medical_utilisations_service_date", "medical_utilisations", ["service_date"], unique=False)
    op.create_index("ix_medical_utilisations_created_by_user_id", "medical_utilisations", ["created_by_user_id"], unique=False)

    op.create_table(
        "medical_authorisations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("authorisation_number", sa.String(length=48), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("benefit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dependant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="pending", nullable=False),
        sa.Column("requested_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("approved_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("provider_name", sa.String(length=200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["member_id"], ["medical_members.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["benefit_id"], ["medical_benefits.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["dependant_id"], ["medical_dependants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("authorisation_number"),
    )
    op.create_index("ix_medical_authorisations_authorisation_number", "medical_authorisations", ["authorisation_number"], unique=True)
    op.create_index("ix_medical_authorisations_member_id", "medical_authorisations", ["member_id"], unique=False)
    op.create_index("ix_medical_authorisations_benefit_id", "medical_authorisations", ["benefit_id"], unique=False)
    op.create_index("ix_medical_authorisations_dependant_id", "medical_authorisations", ["dependant_id"], unique=False)
    op.create_index("ix_medical_authorisations_status", "medical_authorisations", ["status"], unique=False)
    op.create_index("ix_medical_authorisations_created_by_user_id", "medical_authorisations", ["created_by_user_id"], unique=False)

    op.create_table(
        "medical_claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claim_number", sa.String(length=48), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dependant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("claim_kind", sa.String(length=40), server_default="medical", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="submitted", nullable=False),
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column("admission_date", sa.Date(), nullable=True),
        sa.Column("discharge_date", sa.Date(), nullable=True),
        sa.Column("claim_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("approved_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("provider_name", sa.String(length=200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["member_id"], ["medical_members.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dependant_id"], ["medical_dependants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("claim_number"),
    )
    op.create_index("ix_medical_claims_claim_number", "medical_claims", ["claim_number"], unique=True)
    op.create_index("ix_medical_claims_member_id", "medical_claims", ["member_id"], unique=False)
    op.create_index("ix_medical_claims_dependant_id", "medical_claims", ["dependant_id"], unique=False)
    op.create_index("ix_medical_claims_claim_kind", "medical_claims", ["claim_kind"], unique=False)
    op.create_index("ix_medical_claims_status", "medical_claims", ["status"], unique=False)
    op.create_index("ix_medical_claims_service_date", "medical_claims", ["service_date"], unique=False)
    op.create_index("ix_medical_claims_created_by_user_id", "medical_claims", ["created_by_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_medical_claims_created_by_user_id", table_name="medical_claims")
    op.drop_index("ix_medical_claims_service_date", table_name="medical_claims")
    op.drop_index("ix_medical_claims_status", table_name="medical_claims")
    op.drop_index("ix_medical_claims_claim_kind", table_name="medical_claims")
    op.drop_index("ix_medical_claims_dependant_id", table_name="medical_claims")
    op.drop_index("ix_medical_claims_member_id", table_name="medical_claims")
    op.drop_index("ix_medical_claims_claim_number", table_name="medical_claims")
    op.drop_table("medical_claims")

    op.drop_index("ix_medical_authorisations_created_by_user_id", table_name="medical_authorisations")
    op.drop_index("ix_medical_authorisations_status", table_name="medical_authorisations")
    op.drop_index("ix_medical_authorisations_dependant_id", table_name="medical_authorisations")
    op.drop_index("ix_medical_authorisations_benefit_id", table_name="medical_authorisations")
    op.drop_index("ix_medical_authorisations_member_id", table_name="medical_authorisations")
    op.drop_index("ix_medical_authorisations_authorisation_number", table_name="medical_authorisations")
    op.drop_table("medical_authorisations")

    op.drop_index("ix_medical_utilisations_created_by_user_id", table_name="medical_utilisations")
    op.drop_index("ix_medical_utilisations_service_date", table_name="medical_utilisations")
    op.drop_index("ix_medical_utilisations_dependant_id", table_name="medical_utilisations")
    op.drop_index("ix_medical_utilisations_benefit_id", table_name="medical_utilisations")
    op.drop_index("ix_medical_utilisations_member_id", table_name="medical_utilisations")
    op.drop_table("medical_utilisations")

    op.drop_index("ix_medical_dependants_status", table_name="medical_dependants")
    op.drop_index("ix_medical_dependants_relationship_type", table_name="medical_dependants")
    op.drop_index("ix_medical_dependants_member_id", table_name="medical_dependants")
    op.drop_table("medical_dependants")

    op.drop_index("ix_medical_members_created_by_user_id", table_name="medical_members")
    op.drop_index("ix_medical_members_status", table_name="medical_members")
    op.drop_index("ix_medical_members_plan_id", table_name="medical_members")
    op.drop_index("ix_medical_members_customer_id", table_name="medical_members")
    op.drop_index("ix_medical_members_member_number", table_name="medical_members")
    op.drop_table("medical_members")

    op.drop_index("ix_medical_benefits_is_active", table_name="medical_benefits")
    op.drop_index("ix_medical_benefits_category", table_name="medical_benefits")
    op.drop_index("ix_medical_benefits_code", table_name="medical_benefits")
    op.drop_index("ix_medical_benefits_plan_id", table_name="medical_benefits")
    op.drop_table("medical_benefits")

    op.drop_index("ix_medical_plans_is_active", table_name="medical_plans")
    op.drop_index("ix_medical_plans_name", table_name="medical_plans")
    op.drop_index("ix_medical_plans_code", table_name="medical_plans")
    op.drop_table("medical_plans")
