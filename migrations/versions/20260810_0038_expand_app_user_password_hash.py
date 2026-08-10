"""V2.0: ampliar capacidad del hash de contraseña para PostgreSQL.

Revision ID: 20260810_0038
Revises: 20260806_0037
Create Date: 2026-08-10
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260810_0038"
down_revision = "20260806_0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("app_users") as batch_op:
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.String(length=64),
            type_=sa.String(length=255),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("app_users") as batch_op:
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.String(length=255),
            type_=sa.String(length=64),
            existing_nullable=False,
        )
