"""V0.49 selección de factores por dato.

Revision ID: 20260804_0030
Revises: 20260803_0029
Create Date: 2026-08-04
"""
from alembic import op
import sqlalchemy as sa

revision = "20260804_0030"
down_revision = "20260803_0029"
branch_labels = None
depends_on = None

def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "activity_factor_selections" in inspector.get_table_names():
        return
    op.create_table(
        "activity_factor_selections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("activity_data_id", sa.Integer(), sa.ForeignKey("activity_data.id"), nullable=False),
        sa.Column("factor_version_id", sa.Integer(), sa.ForeignKey("emission_factor_versions.id"), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("compatibility_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("selection_status", sa.String(length=30), nullable=False, server_default="Seleccionado"),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("selected_by", sa.String(length=180), nullable=False, server_default="sistema"),
        sa.Column("selected_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_by", sa.String(length=180), nullable=False, server_default=""),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("activity_data_id", "factor_version_id", name="uq_activity_factor_selection"),
    )
    op.create_index("ix_activity_factor_selection_data", "activity_factor_selections", ["activity_data_id"])
    op.create_index("ix_activity_factor_selection_factor", "activity_factor_selections", ["factor_version_id"])

def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "activity_factor_selections" in inspector.get_table_names():
        op.drop_table("activity_factor_selections")
