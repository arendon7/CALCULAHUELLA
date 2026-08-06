"""Ampliar password_hash para formatos de contraseña seguros.

Revision ID: 20260806_0037
Revises: 20260805_0036
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260806_0037"
down_revision = "20260805_0036"
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
    if current_length is not None and current_length >= 255:
        return
    with op.batch_alter_table("app_users") as batch_op:
        batch_op.alter_column(
            "password_hash",
            existing_type=current_type,
            type_=sa.String(length=255),
            existing_nullable=bool(column.get("nullable", False)),
        )


def downgrade() -> None:
    column = _password_column()
    if not column:
        return
    bind = op.get_bind()
    too_long = bind.execute(
        sa.text("SELECT COUNT(*) FROM app_users WHERE length(password_hash) > 64")
    ).scalar_one()
    if too_long:
        raise RuntimeError(
            "No se puede reducir app_users.password_hash a 64: existen hashes más largos."
        )
    with op.batch_alter_table("app_users") as batch_op:
        batch_op.alter_column(
            "password_hash",
            existing_type=column["type"],
            type_=sa.String(length=64),
            existing_nullable=bool(column.get("nullable", False)),
        )
