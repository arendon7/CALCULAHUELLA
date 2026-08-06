"""Ampliar estado de documentos metodológicos.

Revision ID: 20260806_0038
Revises: 20260806_0037
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260806_0038"
down_revision = "20260806_0037"
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
    if current_length is not None and current_length >= 160:
        return
    with op.batch_alter_table("methodology_source_documents") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=current_type,
            type_=sa.String(length=160),
            existing_nullable=bool(column.get("nullable", False)),
        )


def downgrade() -> None:
    column = _status_column()
    if not column:
        return
    bind = op.get_bind()
    too_long = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM methodology_source_documents "
            "WHERE length(status) > 40"
        )
    ).scalar_one()
    if too_long:
        raise RuntimeError(
            "No se puede reducir methodology_source_documents.status a 40: "
            "existen estados más largos."
        )
    with op.batch_alter_table("methodology_source_documents") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=column["type"],
            type_=sa.String(length=40),
            existing_nullable=bool(column.get("nullable", False)),
        )
