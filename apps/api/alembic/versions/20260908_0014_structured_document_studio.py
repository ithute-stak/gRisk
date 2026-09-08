"""add structured TipTap content to document studio

Revision ID: 20260908_0014
Revises: 20260908_0013
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260908_0014"
down_revision: str | None = "20260908_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EMPTY_DOC = sa.text("'{\"type\":\"doc\",\"content\":[]}'::jsonb")


def upgrade() -> None:
    op.add_column(
        "studio_documents",
        sa.Column("content_json", postgresql.JSONB(astext_type=sa.Text()), server_default=_EMPTY_DOC, nullable=False),
    )
    op.add_column(
        "studio_revisions",
        sa.Column("content_json", postgresql.JSONB(astext_type=sa.Text()), server_default=_EMPTY_DOC, nullable=False),
    )


def downgrade() -> None:
    op.drop_column("studio_revisions", "content_json")
    op.drop_column("studio_documents", "content_json")
