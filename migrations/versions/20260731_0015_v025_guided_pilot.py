"""V0.25: guided beta workspace and controlled Greenatics pilot execution."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260731_0015"
down_revision: Union[str, None] = "20260731_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "pilot_executions" not in tables:
        op.create_table(
            "pilot_executions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("pilot_id", sa.Integer(), sa.ForeignKey("pilot_projects.id"), nullable=False),
            sa.Column("inventory_id", sa.Integer(), sa.ForeignKey("inventories.id"), nullable=True),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="No iniciado"),
            sa.Column("started_by", sa.String(length=180), nullable=False, server_default=""),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("target_date", sa.Date(), nullable=True),
            sa.Column("platform_total_tco2e", sa.Float(), nullable=False, server_default="0"),
            sa.Column("independent_total_tco2e", sa.Float(), nullable=True),
            sa.Column("variance_percent", sa.Float(), nullable=True),
            sa.Column("comparison_status", sa.String(length=40), nullable=False, server_default="Pendiente"),
            sa.Column("comparison_notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("approved_by", sa.String(length=180), nullable=False, server_default=""),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("pilot_id", name="uq_pilot_execution_pilot"),
        )
        op.create_index("ix_pilot_executions_pilot_id", "pilot_executions", ["pilot_id"], unique=False)
        op.create_index("ix_pilot_executions_inventory_id", "pilot_executions", ["inventory_id"], unique=False)

    tables = set(sa.inspect(bind).get_table_names())
    if "pilot_execution_source_links" not in tables:
        op.create_table(
            "pilot_execution_source_links",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("execution_id", sa.Integer(), sa.ForeignKey("pilot_executions.id"), nullable=False),
            sa.Column("requirement_id", sa.Integer(), sa.ForeignKey("pilot_source_requirements.id"), nullable=False),
            sa.Column("source_id", sa.Integer(), sa.ForeignKey("emission_sources.id"), nullable=True),
            sa.Column("request_id", sa.Integer(), sa.ForeignKey("data_requests.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("execution_id", "requirement_id", name="uq_pilot_execution_requirement"),
        )
        op.create_index("ix_pilot_execution_source_links_execution_id", "pilot_execution_source_links", ["execution_id"], unique=False)
        op.create_index("ix_pilot_execution_source_links_requirement_id", "pilot_execution_source_links", ["requirement_id"], unique=False)
        op.create_index("ix_pilot_execution_source_links_source_id", "pilot_execution_source_links", ["source_id"], unique=False)
        op.create_index("ix_pilot_execution_source_links_request_id", "pilot_execution_source_links", ["request_id"], unique=False)

    tables = set(sa.inspect(bind).get_table_names())
    if "pilot_issues" not in tables:
        op.create_table(
            "pilot_issues",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("execution_id", sa.Integer(), sa.ForeignKey("pilot_executions.id"), nullable=False),
            sa.Column("code", sa.String(length=60), nullable=False),
            sa.Column("category", sa.String(length=80), nullable=False, server_default="Datos"),
            sa.Column("title", sa.String(length=220), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("severity", sa.String(length=30), nullable=False, server_default="Media"),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="Abierto"),
            sa.Column("owner", sa.String(length=180), nullable=False, server_default="Equipo piloto"),
            sa.Column("due_date", sa.Date(), nullable=True),
            sa.Column("resolution", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_by", sa.String(length=180), nullable=False, server_default="sistema"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("execution_id", "code", name="uq_pilot_issue_code"),
        )
        op.create_index("ix_pilot_issues_execution_id", "pilot_issues", ["execution_id"], unique=False)


def downgrade() -> None:
    # Pilot evidence and lessons are intentionally retained.
    pass
