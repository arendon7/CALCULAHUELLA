"""Compatibilidad con la línea histórica desplegada hasta 20260806_0038.

Revision ID: 20260806_0038
Revises: 20260806_0037

La base PostgreSQL existente llegó a esta revision mediante la línea histórica que
amplió ``app_users.password_hash`` y ``methodology_source_documents.status``.
La rama V2.0 reutilizó 20260806_0037 para work items antes de ser desplegada.
Este checkpoint restaura una revision resoluble para bases existentes y garantiza
el estado estructural histórico sin reducir capacidad ni reescribir datos.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260806_0038"
down_revision = "20260806_0037"
branch_labels = None
depends_on = None


def _column(table: str, name: str):
    bind = op.get_bind()
    inspector = inspect(bind)
    if table not in inspector.get_table_names():
        return None
    return next((column for column in inspector.get_columns(table) if column["name"] == name), None)


def _ensure_min_length(table: str, name: str, minimum: int) -> None:
    column = _column(table, name)
    if not column:
        return
    current_type = column["type"]
    current_length = getattr(current_type, "length", None)
    if current_length is None or current_length >= minimum:
        return
    with op.batch_alter_table(table) as batch_op:
        batch_op.alter_column(
            name,
            existing_type=current_type,
            type_=sa.String(length=minimum),
            existing_nullable=bool(column.get("nullable", False)),
        )


def _guarded_shrink(table: str, name: str, target: int) -> None:
    column = _column(table, name)
    if not column:
        return
    current_type = column["type"]
    current_length = getattr(current_type, "length", None)
    if current_length is not None and current_length <= target:
        return
    bind = op.get_bind()
    too_long = bind.execute(
        sa.text(f"SELECT COUNT(*) FROM {table} WHERE length({name}) > :target"),
        {"target": target},
    ).scalar_one()
    if too_long:
        raise RuntimeError(
            f"No se puede reducir {table}.{name} a {target}: existen valores más largos."
        )
    with op.batch_alter_table(table) as batch_op:
        batch_op.alter_column(
            name,
            existing_type=current_type,
            type_=sa.String(length=target),
            existing_nullable=bool(column.get("nullable", False)),
        )


def upgrade() -> None:
    _ensure_min_length("app_users", "password_hash", 255)
    _ensure_min_length("methodology_source_documents", "status", 160)


def downgrade() -> None:
    # Volver al estado de la revision V2.1 0037 requiere deshacer únicamente las
    # ampliaciones que este checkpoint garantiza. Los guards impiden truncamiento.
    _guarded_shrink("methodology_source_documents", "status", 40)
    _guarded_shrink("app_users", "password_hash", 64)
