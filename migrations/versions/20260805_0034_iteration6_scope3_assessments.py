"""Iteración 6: screening persistente de las 15 categorías de Alcance 3.

Revision ID: 20260805_0034
Revises: 20260805_0033
Create Date: 2026-08-05
"""
from alembic import op
import sqlalchemy as sa

revision = "20260805_0034"
down_revision = "20260805_0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "scope3_category_assessments" in inspector.get_table_names():
        return
    op.create_table(
        "scope3_category_assessments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("inventory_id", sa.Integer(), sa.ForeignKey("inventories.id"), nullable=False),
        sa.Column("category_code", sa.String(length=4), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="Pendiente"),
        sa.Column("relevance_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("owner", sa.String(length=120), nullable=False, server_default="Responsable ambiental"),
        sa.Column("data_strategy", sa.String(length=180), nullable=False, server_default="Por definir"),
        sa.Column("updated_by", sa.String(length=180), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("inventory_id", "category_code", name="uq_scope3_assessment_inventory_category"),
    )
    op.create_index("ix_scope3_assessments_inventory", "scope3_category_assessments", ["inventory_id"])
    op.create_index("ix_scope3_assessments_status", "scope3_category_assessments", ["status"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "scope3_category_assessments" in inspector.get_table_names():
        op.drop_table("scope3_category_assessments")
