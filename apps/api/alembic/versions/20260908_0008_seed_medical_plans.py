"""seed Guardrisk low-cost medical aid plan catalogue

Revision ID: 20260908_0008
Revises: 20260908_0007
Create Date: 2026-09-08
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260908_0008"
down_revision: str | None = "20260908_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PLANS = [
    (uuid.UUID("4a93ba45-b32e-4b37-8b52-d11d1af12e10"), "BASIC-STARTER", "Basic Starter"),
    (uuid.UUID("fa1ea802-70ef-42ec-84c2-4cc57caee3ba"), "BASIC-SAVER", "Basic Saver"),
    (uuid.UUID("145f7aae-0470-42b8-a036-70009f7a7e24"), "BASIC-PLUS", "Basic Plus"),
]


def upgrade() -> None:
    plans = sa.table(
        "medical_plans",
        sa.column("id", postgresql.UUID(as_uuid=True)),
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
                "id": plan_id,
                "code": code,
                "name": name,
                "description": "Guardrisk Low Cost Medical Aid plan. Benefit limits are configured from the approved product schedule.",
                "currency": "LSL",
                "is_active": True,
            }
            for plan_id, code, name in PLANS
        ],
    )


def downgrade() -> None:
    ids = ", ".join(f"'{plan_id}'" for plan_id, _, _ in PLANS)
    op.execute(sa.text(f"DELETE FROM medical_plans WHERE id IN ({ids})"))
