"""seed Guardrisk low-cost medical aid plan catalogue

Revision ID: 20260908_0008
Revises: 20260908_0007
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260908_0008"
down_revision: str | None = "20260908_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PLANS = [
    ("BASIC-STARTER", "Basic Starter"),
    ("BASIC-SAVER", "Basic Saver"),
    ("BASIC-PLUS", "Basic Plus"),
]


def upgrade() -> None:
    plans = sa.table(
        "medical_plans",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("currency", sa.String),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        plans,
        [
            {
                "code": code,
                "name": name,
                "description": "Guardrisk Low Cost Medical Aid plan. Benefit limits are configured from the approved product schedule.",
                "currency": "LSL",
                "is_active": True,
            }
            for code, name in PLANS
        ],
    )


def downgrade() -> None:
    codes = ", ".join(f"'{code}'" for code, _ in PLANS)
    op.execute(sa.text(f"DELETE FROM medical_plans WHERE code IN ({codes})"))
