"""V0.24: security hardening, persistent throttling and audit integrity chain."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260731_0014"
down_revision: Union[str, None] = "20260731_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    audit_columns = {column["name"] for column in inspector.get_columns("audit_events")}
    with op.batch_alter_table("audit_events") as batch:
        if "request_id" not in audit_columns:
            batch.add_column(sa.Column("request_id", sa.String(length=80), nullable=False, server_default=""))
        if "previous_hash" not in audit_columns:
            batch.add_column(sa.Column("previous_hash", sa.String(length=64), nullable=False, server_default=""))
        if "event_hash" not in audit_columns:
            batch.add_column(sa.Column("event_hash", sa.String(length=64), nullable=False, server_default=""))
    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("audit_events")}
    if "ix_audit_events_event_hash" not in indexes:
        op.create_index("ix_audit_events_event_hash", "audit_events", ["event_hash"], unique=False)

    if "login_security_states" not in inspector.get_table_names():
        op.create_table(
            "login_security_states",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("key_hash", sa.String(length=64), nullable=False),
            sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("window_started_at", sa.DateTime(), nullable=True),
            sa.Column("blocked_until", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("key_hash", name="uq_login_security_key_hash"),
        )
        op.create_index("ix_login_security_states_key_hash", "login_security_states", ["key_hash"], unique=True)
        op.create_index("ix_login_security_states_blocked_until", "login_security_states", ["blocked_until"], unique=False)


def downgrade() -> None:
    # Security records and audit hashes are intentionally preserved.
    pass
