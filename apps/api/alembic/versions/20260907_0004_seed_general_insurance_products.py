"""seed Guardrisk general insurance products

Revision ID: 20260907_0004
Revises: 20260907_0003
Create Date: 2026-09-07
"""

from collections.abc import Sequence
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260907_0004"
down_revision: str | None = "20260907_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PRODUCT_CODES = ("BUSINESS", "AGRICULTURAL", "CAR", "PI", "MOTOR")


def upgrade() -> None:
    products = sa.table(
        "insurance_products",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("category", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("is_active", sa.Boolean()),
    )

    op.bulk_insert(
        products,
        [
            {
                "id": uuid.UUID("e75f5b82-2c59-4b93-a534-8e51da2a5c01"),
                "code": "BUSINESS",
                "name": "Business Insurance",
                "category": "General Insurance",
                "description": "Business asset and operational risk insurance.",
                "is_active": True,
            },
            {
                "id": uuid.UUID("e75f5b82-2c59-4b93-a534-8e51da2a5c02"),
                "code": "AGRICULTURAL",
                "name": "Agricultural Insurance",
                "category": "General Insurance",
                "description": "Insurance solutions for agricultural risks and assets.",
                "is_active": True,
            },
            {
                "id": uuid.UUID("e75f5b82-2c59-4b93-a534-8e51da2a5c03"),
                "code": "CAR",
                "name": "Contractors All Risk Insurance",
                "category": "General Insurance",
                "description": "Construction works and associated third-party liability cover.",
                "is_active": True,
            },
            {
                "id": uuid.UUID("e75f5b82-2c59-4b93-a534-8e51da2a5c04"),
                "code": "PI",
                "name": "Professional Indemnity Insurance",
                "category": "General Insurance",
                "description": "Professional liability protection for advice and services.",
                "is_active": True,
            },
            {
                "id": uuid.UUID("e75f5b82-2c59-4b93-a534-8e51da2a5c05"),
                "code": "MOTOR",
                "name": "Motor Insurance",
                "category": "General Insurance",
                "description": "Motor vehicle and fleet insurance cover.",
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM insurance_products "
            "WHERE code IN ('BUSINESS', 'AGRICULTURAL', 'CAR', 'PI', 'MOTOR')"
        )
    )
