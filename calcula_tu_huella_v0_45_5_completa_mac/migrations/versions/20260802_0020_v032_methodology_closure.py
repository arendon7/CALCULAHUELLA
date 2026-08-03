"""V0.32: methodological closure, uncertainty and accounting separation."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260802_0020"
down_revision: Union[str, None] = "20260802_0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(inspector, table: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    source_columns = _columns(inspector, "emission_sources")
    with op.batch_alter_table("emission_sources") as batch:
        if "accounting_treatment" not in source_columns:
            batch.add_column(sa.Column("accounting_treatment", sa.String(length=40), nullable=False, server_default="Emisión bruta"))
        if "scope2_method" not in source_columns:
            batch.add_column(sa.Column("scope2_method", sa.String(length=30), nullable=False, server_default="No aplica"))
        if "biogenic_origin" not in source_columns:
            batch.add_column(sa.Column("biogenic_origin", sa.String(length=80), nullable=False, server_default="No aplica"))

    activity_columns = _columns(sa.inspect(bind), "activity_data")
    with op.batch_alter_table("activity_data") as batch:
        if "uncertainty_percentage" not in activity_columns:
            batch.add_column(sa.Column("uncertainty_percentage", sa.Float(), nullable=False, server_default="0"))
        if "uncertainty_basis" not in activity_columns:
            batch.add_column(sa.Column("uncertainty_basis", sa.String(length=180), nullable=False, server_default=""))

    calculation_columns = _columns(sa.inspect(bind), "emission_calculations")
    with op.batch_alter_table("emission_calculations") as batch:
        if "reporting_bucket" not in calculation_columns:
            batch.add_column(sa.Column("reporting_bucket", sa.String(length=40), nullable=False, server_default="Emisión bruta"))
        if "uncertainty_percentage" not in calculation_columns:
            batch.add_column(sa.Column("uncertainty_percentage", sa.Float(), nullable=False, server_default="0"))
        if "lower_co2e_kg" not in calculation_columns:
            batch.add_column(sa.Column("lower_co2e_kg", sa.Float(), nullable=False, server_default="0"))
        if "upper_co2e_kg" not in calculation_columns:
            batch.add_column(sa.Column("upper_co2e_kg", sa.Float(), nullable=False, server_default="0"))

    if "base_year_recalculations" not in tables:
        op.create_table(
            "base_year_recalculations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("inventory_id", sa.Integer(), sa.ForeignKey("inventories.id"), nullable=False),
            sa.Column("event_date", sa.Date(), nullable=False),
            sa.Column("trigger_type", sa.String(length=100), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("previous_total_tco2e", sa.Float(), nullable=False, server_default="0"),
            sa.Column("recalculated_total_tco2e", sa.Float(), nullable=False, server_default="0"),
            sa.Column("change_percentage", sa.Float(), nullable=False, server_default="0"),
            sa.Column("threshold_percentage", sa.Float(), nullable=False, server_default="5"),
            sa.Column("decision", sa.String(length=40), nullable=False, server_default="Evaluar"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="Pendiente"),
            sa.Column("requested_by", sa.String(length=180), nullable=False, server_default=""),
            sa.Column("reviewed_by", sa.String(length=180), nullable=False, server_default=""),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_base_year_recalculations_inventory_id", "base_year_recalculations", ["inventory_id"], unique=False)


def downgrade() -> None:
    # Methodological audit data is retained intentionally.
    pass
