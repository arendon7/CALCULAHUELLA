"""Iteración 8: huella de producto, proyectos de mitigación y aseguramiento.

Revision ID: 20260805_0036
Revises: 20260805_0035
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260805_0036"
down_revision = "20260805_0035"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind(); tables=set(inspect(bind).get_table_names())
    if "product_footprint_studies" not in tables:
        op.create_table("product_footprint_studies",
            sa.Column("id", sa.Integer(), primary_key=True), sa.Column("inventory_id", sa.Integer(), sa.ForeignKey("inventories.id"), nullable=False),
            sa.Column("product_name", sa.String(180), nullable=False), sa.Column("product_code", sa.String(80), nullable=False, server_default=""),
            sa.Column("declared_unit", sa.String(100), nullable=False), sa.Column("reference_flow", sa.Float(), nullable=False, server_default="1"),
            sa.Column("boundary", sa.String(60), nullable=False, server_default="De la cuna a la puerta"),
            sa.Column("methodology", sa.String(180), nullable=False, server_default="ISO 14067:2018"),
            sa.Column("pcr_reference", sa.String(240), nullable=False, server_default=""), sa.Column("allocation_method", sa.String(180), nullable=False, server_default="Sin asignación"),
            sa.Column("cutoff_rule_percent", sa.Float(), nullable=False, server_default="1"), sa.Column("biogenic_treatment", sa.String(180), nullable=False, server_default="Reporte separado"),
            sa.Column("land_use_included", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("data_quality_rating", sa.String(20), nullable=False, server_default="C"),
            sa.Column("status", sa.String(30), nullable=False, server_default="Borrador"), sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_by", sa.String(180), nullable=False, server_default=""), sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("reviewed_by", sa.String(180), nullable=False, server_default=""), sa.Column("reviewed_at", sa.DateTime(), nullable=True))
        op.create_index("ix_product_footprint_studies_inventory_id", "product_footprint_studies", ["inventory_id"])
    if "product_lifecycle_stages" not in tables:
        op.create_table("product_lifecycle_stages",
            sa.Column("id", sa.Integer(), primary_key=True), sa.Column("study_id", sa.Integer(), sa.ForeignKey("product_footprint_studies.id"), nullable=False),
            sa.Column("stage_code", sa.String(30), nullable=False), sa.Column("stage_name", sa.String(120), nullable=False), sa.Column("accounting_type", sa.String(40), nullable=False, server_default="Emisión"),
            sa.Column("activity_name", sa.String(180), nullable=False), sa.Column("activity_value", sa.Float(), nullable=False, server_default="0"), sa.Column("activity_unit", sa.String(40), nullable=False, server_default="unidad"),
            sa.Column("factor_value", sa.Float(), nullable=False, server_default="0"), sa.Column("factor_output_unit", sa.String(40), nullable=False, server_default="kg CO2e"),
            sa.Column("calculated_tco2e", sa.Float(), nullable=False, server_default="0"), sa.Column("data_source", sa.String(240), nullable=False, server_default=""),
            sa.Column("geography", sa.String(100), nullable=False, server_default=""), sa.Column("reference_year", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("uncertainty_percentage", sa.Float(), nullable=False, server_default="0"), sa.Column("evidence_reference", sa.String(240), nullable=False, server_default=""),
            sa.Column("excluded", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("exclusion_reason", sa.String(280), nullable=False, server_default=""),
            sa.Column("created_by", sa.String(180), nullable=False, server_default=""), sa.Column("created_at", sa.DateTime(), nullable=False))
        op.create_index("ix_product_lifecycle_stages_study_id", "product_lifecycle_stages", ["study_id"])
    if "mitigation_projects" not in tables:
        op.create_table("mitigation_projects",
            sa.Column("id", sa.Integer(), primary_key=True), sa.Column("inventory_id", sa.Integer(), sa.ForeignKey("inventories.id"), nullable=False),
            sa.Column("name", sa.String(180), nullable=False), sa.Column("project_type", sa.String(100), nullable=False, server_default="Reducción de emisiones"),
            sa.Column("methodology", sa.String(220), nullable=False, server_default="ISO 14064-2:2019"), sa.Column("baseline_scenario", sa.Text(), nullable=False),
            sa.Column("project_scenario", sa.Text(), nullable=False), sa.Column("additionality_basis", sa.Text(), nullable=False, server_default=""),
            sa.Column("monitoring_plan", sa.Text(), nullable=False, server_default=""), sa.Column("leakage_sources", sa.Text(), nullable=False, server_default=""),
            sa.Column("ownership_statement", sa.Text(), nullable=False, server_default=""), sa.Column("double_counting_control", sa.Text(), nullable=False, server_default=""),
            sa.Column("start_date", sa.Date(), nullable=False), sa.Column("end_date", sa.Date(), nullable=False),
            sa.Column("estimated_baseline_tco2e", sa.Float(), nullable=False, server_default="0"), sa.Column("estimated_project_tco2e", sa.Float(), nullable=False, server_default="0"),
            sa.Column("estimated_leakage_tco2e", sa.Float(), nullable=False, server_default="0"), sa.Column("estimated_removals_tco2e", sa.Float(), nullable=False, server_default="0"),
            sa.Column("estimated_reduction_tco2e", sa.Float(), nullable=False, server_default="0"), sa.Column("status", sa.String(30), nullable=False, server_default="Diseño"),
            sa.Column("created_by", sa.String(180), nullable=False, server_default=""), sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("reviewed_by", sa.String(180), nullable=False, server_default=""), sa.Column("reviewed_at", sa.DateTime(), nullable=True))
        op.create_index("ix_mitigation_projects_inventory_id", "mitigation_projects", ["inventory_id"])
    if "mitigation_monitoring_periods" not in tables:
        op.create_table("mitigation_monitoring_periods",
            sa.Column("id", sa.Integer(), primary_key=True), sa.Column("project_id", sa.Integer(), sa.ForeignKey("mitigation_projects.id"), nullable=False),
            sa.Column("period_start", sa.Date(), nullable=False), sa.Column("period_end", sa.Date(), nullable=False),
            sa.Column("baseline_tco2e", sa.Float(), nullable=False, server_default="0"), sa.Column("project_tco2e", sa.Float(), nullable=False, server_default="0"),
            sa.Column("leakage_tco2e", sa.Float(), nullable=False, server_default="0"), sa.Column("removals_tco2e", sa.Float(), nullable=False, server_default="0"),
            sa.Column("reduction_tco2e", sa.Float(), nullable=False, server_default="0"), sa.Column("uncertainty_percentage", sa.Float(), nullable=False, server_default="0"),
            sa.Column("evidence_reference", sa.String(260), nullable=False, server_default=""), sa.Column("status", sa.String(30), nullable=False, server_default="Borrador"),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""), sa.Column("created_by", sa.String(180), nullable=False, server_default=""), sa.Column("created_at", sa.DateTime(), nullable=False))
        op.create_index("ix_mitigation_monitoring_periods_project_id", "mitigation_monitoring_periods", ["project_id"])
    if "assurance_engagements" not in tables:
        op.create_table("assurance_engagements",
            sa.Column("id", sa.Integer(), primary_key=True), sa.Column("inventory_id", sa.Integer(), sa.ForeignKey("inventories.id"), nullable=False),
            sa.Column("subject_type", sa.String(40), nullable=False, server_default="Inventario corporativo"), sa.Column("subject_reference", sa.String(120), nullable=False, server_default=""),
            sa.Column("engagement_type", sa.String(30), nullable=False, server_default="Verificación"), sa.Column("standard", sa.String(120), nullable=False, server_default="ISO 14064-3:2019"),
            sa.Column("assurance_level", sa.String(30), nullable=False, server_default="Limitado"), sa.Column("materiality_percent", sa.Float(), nullable=False, server_default="5"),
            sa.Column("criteria", sa.Text(), nullable=False), sa.Column("scope", sa.Text(), nullable=False), sa.Column("verifier_organization", sa.String(180), nullable=False),
            sa.Column("lead_verifier", sa.String(180), nullable=False), sa.Column("independence_declaration", sa.Text(), nullable=False, server_default=""),
            sa.Column("competence_basis", sa.Text(), nullable=False, server_default=""), sa.Column("start_date", sa.Date(), nullable=False), sa.Column("end_date", sa.Date(), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="Planificado"), sa.Column("conclusion", sa.Text(), nullable=False, server_default=""),
            sa.Column("opinion", sa.String(60), nullable=False, server_default=""), sa.Column("statement_date", sa.Date(), nullable=True),
            sa.Column("created_by", sa.String(180), nullable=False, server_default=""), sa.Column("created_at", sa.DateTime(), nullable=False))
        op.create_index("ix_assurance_engagements_inventory_id", "assurance_engagements", ["inventory_id"])
    if "assurance_findings" not in tables:
        op.create_table("assurance_findings",
            sa.Column("id", sa.Integer(), primary_key=True), sa.Column("engagement_id", sa.Integer(), sa.ForeignKey("assurance_engagements.id"), nullable=False),
            sa.Column("area", sa.String(120), nullable=False, server_default="General"), sa.Column("title", sa.String(180), nullable=False), sa.Column("description", sa.Text(), nullable=False),
            sa.Column("severity", sa.String(30), nullable=False, server_default="Menor"), sa.Column("status", sa.String(30), nullable=False, server_default="Abierto"),
            sa.Column("evidence_reference", sa.String(260), nullable=False, server_default=""), sa.Column("management_response", sa.Text(), nullable=False, server_default=""),
            sa.Column("verifier_conclusion", sa.Text(), nullable=False, server_default=""), sa.Column("created_by", sa.String(180), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("closed_at", sa.DateTime(), nullable=True))
        op.create_index("ix_assurance_findings_engagement_id", "assurance_findings", ["engagement_id"])


def downgrade():
    for table, index in reversed([
        ("product_footprint_studies", "ix_product_footprint_studies_inventory_id"),
        ("product_lifecycle_stages", "ix_product_lifecycle_stages_study_id"),
        ("mitigation_projects", "ix_mitigation_projects_inventory_id"),
        ("mitigation_monitoring_periods", "ix_mitigation_monitoring_periods_project_id"),
        ("assurance_engagements", "ix_assurance_engagements_inventory_id"),
        ("assurance_findings", "ix_assurance_findings_engagement_id"),
    ]):
        if table in inspect(op.get_bind()).get_table_names():
            op.drop_index(index, table_name=table); op.drop_table(table)
