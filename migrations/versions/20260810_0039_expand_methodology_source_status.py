"""V2.0: garantizar capacidad descriptiva de fuentes metodológicas.

Revision ID: 20260810_0039
Revises: 20260810_0038
Create Date: 2026-08-10

La base histórica desplegada ya usa VARCHAR(160). Esta revision no puede reducir
esa capacidad a 100; únicamente amplía cuando la columna existente es menor.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260810_0039"
down_revision = "20260810_0038"
branch_labels = None
depends_on = None


def _status_column():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "methodology_source_documents" not in inspector.get_table_names():
        return None
    return next(
        (
            column
            for column in inspector.get_columns("methodology_source_documents")
            if column["name"] == "status"
        ),
        None,
    )


def upgrade() -> None:
    column = _status_column()
    if not column:
        return
    current_type = column["type"]
    current_length = getattr(current_type, "length", None)
    if current_length is None or current_length >= 160:
        return
    with op.batch_alter_table("methodology_source_documents") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=current_type,
            type_=sa.String(length=160),
            existing_nullable=bool(column.get("nullable", False)),
        )


def downgrade() -> None:
    # El padre histórico 20260806_0038 ya garantiza VARCHAR(160).
    return
