"""V0.26: controlled real-data intake and quality findings."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260801_0016"
down_revision: Union[str, None] = "20260731_0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())

    if "data_import_batches" not in tables:
        op.create_table(
            "data_import_batches",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("execution_id", sa.Integer(), sa.ForeignKey("pilot_executions.id"), nullable=True),
            sa.Column("code", sa.String(length=80), nullable=False),
            sa.Column("filename", sa.String(length=220), nullable=False),
            sa.Column("file_hash", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="Cargado"),
            sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("valid_rows", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("warning_rows", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_rows", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("applied_rows", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("quality_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("uploaded_by", sa.String(length=180), nullable=False, server_default="sistema"),
            sa.Column("uploaded_at", sa.DateTime(), nullable=False),
            sa.Column("validated_at", sa.DateTime(), nullable=True),
            sa.Column("applied_at", sa.DateTime(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.UniqueConstraint("organization_id", "file_hash", name="uq_data_import_org_hash"),
            sa.UniqueConstraint("code", name="uq_data_import_batches_code"),
        )
        op.create_index("ix_data_import_batches_organization_id", "data_import_batches", ["organization_id"], unique=False)
        op.create_index("ix_data_import_batches_execution_id", "data_import_batches", ["execution_id"], unique=False)
        op.create_index("ix_data_import_batches_code", "data_import_batches", ["code"], unique=True)

    tables = set(sa.inspect(bind).get_table_names())
    if "data_import_rows" not in tables:
        op.create_table(
            "data_import_rows",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("batch_id", sa.Integer(), sa.ForeignKey("data_import_batches.id"), nullable=False),
            sa.Column("row_number", sa.Integer(), nullable=False),
            sa.Column("requirement_code", sa.String(length=80), nullable=False, server_default=""),
            sa.Column("source_id", sa.Integer(), sa.ForeignKey("emission_sources.id"), nullable=True),
            sa.Column("period_start", sa.Date(), nullable=True),
            sa.Column("period_end", sa.Date(), nullable=True),
            sa.Column("value", sa.Float(), nullable=True),
            sa.Column("unit", sa.String(length=40), nullable=False, server_default=""),
            sa.Column("evidence_reference", sa.String(length=300), nullable=False, server_default=""),
            sa.Column("data_origin", sa.String(length=80), nullable=False, server_default="Registro operativo"),
            sa.Column("is_estimated", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("quality_level", sa.String(length=20), nullable=False, server_default="D"),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="Pendiente"),
            sa.Column("validation_messages", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("activity_data_id", sa.Integer(), sa.ForeignKey("activity_data.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("batch_id", "row_number", name="uq_data_import_batch_row"),
        )
        op.create_index("ix_data_import_rows_batch_id", "data_import_rows", ["batch_id"], unique=False)
        op.create_index("ix_data_import_rows_source_id", "data_import_rows", ["source_id"], unique=False)
        op.create_index("ix_data_import_rows_activity_data_id", "data_import_rows", ["activity_data_id"], unique=False)

    tables = set(sa.inspect(bind).get_table_names())
    if "data_quality_findings" not in tables:
        op.create_table(
            "data_quality_findings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("batch_id", sa.Integer(), sa.ForeignKey("data_import_batches.id"), nullable=False),
            sa.Column("row_id", sa.Integer(), sa.ForeignKey("data_import_rows.id"), nullable=True),
            sa.Column("rule_code", sa.String(length=80), nullable=False),
            sa.Column("severity", sa.String(length=30), nullable=False, server_default="Advertencia"),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="Abierto"),
            sa.Column("resolution", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_data_quality_findings_batch_id", "data_quality_findings", ["batch_id"], unique=False)
        op.create_index("ix_data_quality_findings_row_id", "data_quality_findings", ["row_id"], unique=False)


def downgrade() -> None:
    # Quality-control evidence is intentionally retained.
    pass
