"""V0.42 reconciliada: ensayos de despliegue e incidentes operativos."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260803_0026"
down_revision: Union[str, None] = "20260803_0025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "deployment_rehearsals" not in tables:
        op.create_table(
            "deployment_rehearsals",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="En ejecución"),
            sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("strict_mode", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("environment", sa.String(30), nullable=False, server_default="local"),
            sa.Column("database_backend", sa.String(40), nullable=False, server_default=""),
            sa.Column("storage_backend", sa.String(40), nullable=False, server_default=""),
            sa.Column("checks_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("blockers_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("warnings_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("performed_by", sa.String(180), nullable=False, server_default=""),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        )
        op.create_index("ix_deployment_rehearsals_organization_id", "deployment_rehearsals", ["organization_id"])
        op.create_index("ix_deployment_rehearsals_status", "deployment_rehearsals", ["status"])
    if "operational_incidents" not in tables:
        op.create_table(
            "operational_incidents",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("fingerprint", sa.String(64), nullable=False),
            sa.Column("title", sa.String(220), nullable=False),
            sa.Column("severity", sa.String(30), nullable=False, server_default="Media"),
            sa.Column("status", sa.String(30), nullable=False, server_default="Abierto"),
            sa.Column("source", sa.String(80), nullable=False, server_default="Puerta productiva"),
            sa.Column("detail", sa.Text(), nullable=False, server_default=""),
            sa.Column("occurrence_count", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("first_seen_at", sa.DateTime(), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(), nullable=False),
            sa.Column("acknowledged_by", sa.String(180), nullable=False, server_default=""),
            sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
            sa.Column("resolved_by", sa.String(180), nullable=False, server_default=""),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("organization_id", "fingerprint", name="uq_operational_incident_fingerprint"),
        )
        op.create_index("ix_operational_incidents_organization_id", "operational_incidents", ["organization_id"])
        op.create_index("ix_operational_incidents_fingerprint", "operational_incidents", ["fingerprint"])
        op.create_index("ix_operational_incidents_severity", "operational_incidents", ["severity"])
        op.create_index("ix_operational_incidents_status", "operational_incidents", ["status"])


def downgrade() -> None:
    op.drop_table("operational_incidents")
    op.drop_table("deployment_rehearsals")
