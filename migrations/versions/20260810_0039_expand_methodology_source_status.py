"""V2.0: ampliar estados descriptivos de fuentes metodológicas.

Revision ID: 20260810_0039
Revises: 20260810_0038
Create Date: 2026-08-10
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260810_0039"
down_revision = "20260810_0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("methodology_source_documents") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=40),
            type_=sa.String(length=100),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("methodology_source_documents") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=100),
            type_=sa.String(length=40),
            existing_nullable=False,
        )
