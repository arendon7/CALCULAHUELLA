"""V0.27: monthly reconciliation, review and immutable period close."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260801_0017"
down_revision: Union[str, None] = "20260801_0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "period_closes" not in tables:
        op.create_table(
            "period_closes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("inventory_id", sa.Integer(), sa.ForeignKey("inventories.id"), nullable=False),
            sa.Column("period_start", sa.Date(), nullable=False),
            sa.Column("period_end", sa.Date(), nullable=False),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="Abierto"),
            sa.Column("expected_sources", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("ready_sources", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("blocked_sources", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("data_coverage_percent", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("evidence_coverage_percent", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("quality_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_tco2e", sa.Float(), nullable=False, server_default="0"),
            sa.Column("blockers_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("snapshot_hash", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("snapshot_json", sa.Text(), nullable=False, server_default=""),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("submitted_by", sa.String(length=180), nullable=False, server_default=""),
            sa.Column("submitted_at", sa.DateTime(), nullable=True),
            sa.Column("closed_by", sa.String(length=180), nullable=False, server_default=""),
            sa.Column("closed_at", sa.DateTime(), nullable=True),
            sa.Column("reopened_by", sa.String(length=180), nullable=False, server_default=""),
            sa.Column("reopened_at", sa.DateTime(), nullable=True),
            sa.Column("reopen_reason", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("inventory_id", "period_start", "period_end", name="uq_period_close_inventory_period"),
        )
        op.create_index("ix_period_closes_organization_id", "period_closes", ["organization_id"], unique=False)
        op.create_index("ix_period_closes_inventory_id", "period_closes", ["inventory_id"], unique=False)
        op.create_index("ix_period_closes_snapshot_hash", "period_closes", ["snapshot_hash"], unique=False)

    tables = set(sa.inspect(bind).get_table_names())
    if "period_close_items" not in tables:
        op.create_table(
            "period_close_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("period_close_id", sa.Integer(), sa.ForeignKey("period_closes.id"), nullable=False),
            sa.Column("source_id", sa.Integer(), sa.ForeignKey("emission_sources.id"), nullable=False),
            sa.Column("source_code", sa.String(length=80), nullable=False, server_default=""),
            sa.Column("source_name", sa.String(length=220), nullable=False, server_default=""),
            sa.Column("site", sa.String(length=120), nullable=False, server_default=""),
            sa.Column("scope", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("activity_records", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("estimated_records", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("quality_level", sa.String(length=20), nullable=False, server_default="D"),
            sa.Column("calculation_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("emissions_tco2e", sa.Float(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="Pendiente"),
            sa.Column("snapshot_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("period_close_id", "source_id", name="uq_period_close_item_source"),
        )
        op.create_index("ix_period_close_items_period_close_id", "period_close_items", ["period_close_id"], unique=False)
        op.create_index("ix_period_close_items_source_id", "period_close_items", ["source_id"], unique=False)


def downgrade() -> None:
    # Closed-period evidence is intentionally retained.
    pass
