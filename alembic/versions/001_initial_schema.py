"""Initial schema — creates candidates and resumes tables.

Revision ID: 001
Revises:
Create Date: 2026-04-03 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Detect dialect at migration time
_IS_SQLITE: bool = False


def _is_sqlite() -> bool:
    """Return True when the active dialect is SQLite."""
    bind = op.get_bind()
    return bind.dialect.name == "sqlite"


def upgrade() -> None:
    """Create candidates and resumes tables."""
    sqlite = _is_sqlite()

    op.create_table(
        "candidates",
        sa.Column("id", sa.String(36) if sqlite else sa.dialects.postgresql.UUID(as_uuid=False) if not sqlite else sa.String(36), primary_key=True),  # type: ignore[attr-defined]
        sa.Column("full_name", sa.Text, nullable=False),
        sa.Column("email", sa.Text, nullable=True),
        sa.Column("phone", sa.Text, nullable=True),
        sa.Column("location", sa.Text, nullable=True),
        sa.Column("linkedin_url", sa.Text, nullable=True),
        sa.Column("github_url", sa.Text, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("skills", sa.Text, nullable=True),
        sa.Column("languages", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "resumes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "candidate_id",
            sa.String(36),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("raw_text", sa.Text, nullable=True),
        sa.Column("source_filename", sa.Text, nullable=True),
        sa.Column("json_path", sa.Text, nullable=True),
        sa.Column("education", sa.Text, nullable=True),
        sa.Column("experience", sa.Text, nullable=True),
        sa.Column("certifications", sa.Text, nullable=True),
        sa.Column(
            "parsed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index("idx_resumes_candidate_id", "resumes", ["candidate_id"])


def downgrade() -> None:
    """Drop candidates and resumes tables."""
    op.drop_index("idx_resumes_candidate_id", table_name="resumes")
    op.drop_table("resumes")
    op.drop_table("candidates")
