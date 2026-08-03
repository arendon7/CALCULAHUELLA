"""V0.34: operational hardening and restore rehearsal records."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260802_0022"
down_revision: Union[str, None] = "20260802_0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "restore_drills" not in tables:
        op.create_table(
            "restore_drills",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("backup_name", sa.String(length=240), nullable=False),
            sa.Column("backup_sha256", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("application_version", sa.String(length=30), nullable=False, server_default=""),
            sa.Column("database_backend", sa.String(length=40), nullable=False, server_default=""),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="En ejecución"),
            sa.Column("integrity_result", sa.String(length=80), nullable=False, server_default=""),
            sa.Column("table_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("record_summary_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("checks_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("performed_by", sa.String(length=180), nullable=False, server_default=""),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        )
        op.create_index("ix_restore_drills_organization_id", "restore_drills", ["organization_id"], unique=False)
        op.create_index("ix_restore_drills_backup_name", "restore_drills", ["backup_name"], unique=False)
        op.create_index("ix_restore_drills_status", "restore_drills", ["status"], unique=False)


def downgrade() -> None:
    # Operational evidence is retained intentionally.
    pass
