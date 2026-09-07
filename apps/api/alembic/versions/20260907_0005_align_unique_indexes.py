"""align redundant unique constraints with SQLAlchemy metadata

Revision ID: 20260907_0005
Revises: 20260907_0004
Create Date: 2026-09-07

The affected columns already have unique indexes. Earlier migrations also
created redundant PostgreSQL UNIQUE constraints for the same columns.
SQLAlchemy models use unique indexed columns, so remove only the duplicate
constraints while preserving uniqueness through the existing indexes.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260907_0005"
down_revision: str | None = "20260907_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REDUNDANT_UNIQUE_CONSTRAINTS = (
    ("roles", "roles_name_key", "name"),
    ("users", "users_email_key", "email"),
    ("customers", "customers_customer_number_key", "customer_number"),
    ("insurance_products", "insurance_products_code_key", "code"),
    ("quotes", "quotes_quote_number_key", "quote_number"),
    ("policies", "policies_policy_number_key", "policy_number"),
)


def upgrade() -> None:
    for table_name, constraint_name, _ in REDUNDANT_UNIQUE_CONSTRAINTS:
        op.drop_constraint(constraint_name, table_name, type_="unique")


def downgrade() -> None:
    for table_name, constraint_name, column_name in REDUNDANT_UNIQUE_CONSTRAINTS:
        op.create_unique_constraint(constraint_name, table_name, [column_name])
