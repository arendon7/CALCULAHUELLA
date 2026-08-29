"""V2.0: garantizar capacidad segura del hash de contraseña.

Revision ID: 20260810_0038
Revises: 20260806_0038
Create Date: 2026-08-10

Esta revision permanece como checkpoint de la rama V2.0, pero ya no asume que
la columna parte de VARCHAR(64). Bases históricas desplegadas pueden llegar con
VARCHAR(255); por tanto el upgrade es idempotente y nunca reduce capacidad.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260810_0038"
down_revision = "20260806_0038"
branch_labels = None
depends_on = None


def _password_column():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "app_users" not in inspector.get_table_names():
        return None
    return next(
        (column for column in inspector.get_columns("app_users") if column["name"] == "password_hash"),
        None,
    )


def upgrade() -> None:
    column = _password_column()
    if not column:
        return
    current_type = column["type"]
    current_length = getattr(current_type, "length", None)
    if current_length is None or current_length >= 255:
        return
    with op.batch_alter_table("app_users") as batch_op:
        batch_op.alter_column(
            "password_hash",
            existing_type=current_type,
            type_=sa.String(length=255),
            existing_nullable=bool(column.get("nullable", False)),
        )


def downgrade() -> None:
    # El padre 20260806_0038 ya garantiza VARCHAR(255), por lo que reducir aquí
    # rompería el contrato histórico. El downgrade es deliberadamente idempotente.
    return
