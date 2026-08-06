"""Iteración 7: libro mayor de tierras, remociones y carbono biogénico.

Revision ID: 20260805_0035
Revises: 20260805_0034
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260805_0035"
down_revision = "20260805_0034"
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    if "land_carbon_entries" in inspect(bind).get_table_names():
        return
    op.create_table(
        "land_carbon_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("inventory_id", sa.Integer(), sa.ForeignKey("inventories.id"), nullable=False),
        sa.Column("entry_type", sa.String(50), nullable=False),
        sa.Column("activity_name", sa.String(180), nullable=False),
        sa.Column("land_category", sa.String(100), nullable=False, server_default="No aplica"),
        sa.Column("carbon_pool", sa.String(100), nullable=False, server_default="No aplica"),
        sa.Column("location", sa.String(160), nullable=False, server_default=""),
        sa.Column("reporting_scope", sa.String(30), nullable=False, server_default="Fuera de alcances"),
        sa.Column("gas", sa.String(30), nullable=False, server_default="CO2"),
        sa.Column("quantity_tco2e", sa.Float(), nullable=False, server_default="0"),
        sa.Column("start_date", sa.Date(), nullable=False), sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("methodology", sa.String(220), nullable=False, server_default=""),
        sa.Column("source_reference", sa.String(300), nullable=False, server_default=""),
        sa.Column("traceability_level", sa.String(40), nullable=False, server_default="País de origen"),
        sa.Column("uncertainty_percentage", sa.Float(), nullable=False, server_default="0"),
        sa.Column("storage_duration_years", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reversal_monitoring", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("additionality_claimed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("lifecycle_complete", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(30), nullable=False, server_default="Borrador"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", sa.String(180), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_by", sa.String(180), nullable=False, server_default=""),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_land_carbon_entries_inventory_id", "land_carbon_entries", ["inventory_id"])

def downgrade():
    bind = op.get_bind()
    if "land_carbon_entries" not in inspect(bind).get_table_names():
        return
    op.drop_index("ix_land_carbon_entries_inventory_id", table_name="land_carbon_entries")
    op.drop_table("land_carbon_entries")
