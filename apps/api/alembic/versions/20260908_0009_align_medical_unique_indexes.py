"""align medical unique indexes with SQLAlchemy metadata

Revision ID: 20260908_0009
Revises: 20260908_0008
Create Date: 2026-09-08

The affected columns already have unique indexes. The initial medical migration
also created redundant PostgreSQL UNIQUE constraints for the same columns.
Keep the unique indexes and remove only those duplicate constraints.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260908_0009"
down_revision: str | None = "20260908_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REDUNDANT_UNIQUE_CONSTRAINTS = (
    ("medical_plans", "medical_plans_code_key", "code"),
    ("medical_members", "medical_members_member_number_key", "member_number"),
    (
        "medical_authorisations",
        "medical_authorisations_authorisation_number_key",
        "authorisation_number",
    ),
    ("medical_claims", "medical_claims_claim_number_key", "claim_number"),
)


def upgrade() -> None:
    for table_name, constraint_name, _ in REDUNDANT_UNIQUE_CONSTRAINTS:
        op.drop_constraint(constraint_name, table_name, type_="unique")


def downgrade() -> None:
    for table_name, constraint_name, column_name in REDUNDANT_UNIQUE_CONSTRAINTS:
        op.create_unique_constraint(constraint_name, table_name, [column_name])
