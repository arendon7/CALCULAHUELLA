"""V0.33: Greenatics pilot control tower and source-level reconciliation."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260802_0021"
down_revision: Union[str, None] = "20260802_0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "pilot_source_comparisons" not in tables:
        op.create_table(
            "pilot_source_comparisons",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("execution_id", sa.Integer(), sa.ForeignKey("pilot_executions.id"), nullable=False),
            sa.Column("requirement_id", sa.Integer(), sa.ForeignKey("pilot_source_requirements.id"), nullable=False),
            sa.Column("source_id", sa.Integer(), sa.ForeignKey("emission_sources.id"), nullable=True),
            sa.Column("platform_tco2e", sa.Float(), nullable=False, server_default="0"),
            sa.Column("independent_tco2e", sa.Float(), nullable=True),
            sa.Column("absolute_difference_tco2e", sa.Float(), nullable=True),
            sa.Column("variance_percent", sa.Float(), nullable=True),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="Pendiente"),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("reviewed_by", sa.String(length=180), nullable=False, server_default=""),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("execution_id", "requirement_id", name="uq_pilot_source_comparison"),
        )
        op.create_index("ix_pilot_source_comparisons_execution_id", "pilot_source_comparisons", ["execution_id"], unique=False)
        op.create_index("ix_pilot_source_comparisons_requirement_id", "pilot_source_comparisons", ["requirement_id"], unique=False)
        op.create_index("ix_pilot_source_comparisons_source_id", "pilot_source_comparisons", ["source_id"], unique=False)


def downgrade() -> None:
    # Reconciliation evidence is retained intentionally.
    pass
