"""V0.45 product intelligence, organizational profile and implementation route.

Revision ID: 20260803_0029
Revises: 20260803_0028
Create Date: 2026-08-03
"""

from alembic import op
import sqlalchemy as sa

revision = "20260803_0029"
down_revision = "20260803_0028"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existing = _tables()
    if "organization_carbon_profiles" not in existing:
        op.create_table(
            "organization_carbon_profiles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("company_size", sa.String(length=40), nullable=False, server_default="Por definir"),
            sa.Column("business_model", sa.String(length=160), nullable=False, server_default=""),
            sa.Column("sector_subsector", sa.String(length=180), nullable=False, server_default=""),
            sa.Column("operating_description", sa.Text(), nullable=False, server_default=""),
            sa.Column("countries_count", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("countries_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("facility_types_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("core_processes_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("energy_sources_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("fleet_profile", sa.Text(), nullable=False, server_default=""),
            sa.Column("refrigerants_profile", sa.Text(), nullable=False, server_default=""),
            sa.Column("waste_profile", sa.Text(), nullable=False, server_default=""),
            sa.Column("wastewater_profile", sa.Text(), nullable=False, server_default=""),
            sa.Column("agriculture_land_use_profile", sa.Text(), nullable=False, server_default=""),
            sa.Column("key_materials_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("supplier_profile", sa.Text(), nullable=False, server_default=""),
            sa.Column("reporting_drivers_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("climate_goals_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("current_data_systems_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("inventory_history", sa.String(length=80), nullable=False, server_default="Sin inventario anterior"),
            sa.Column("data_availability", sa.String(length=60), nullable=False, server_default="Baja"),
            sa.Column("evidence_readiness", sa.String(length=60), nullable=False, server_default="Baja"),
            sa.Column("reporting_frequency", sa.String(length=40), nullable=False, server_default="Anual"),
            sa.Column("assurance_ambition", sa.String(length=80), nullable=False, server_default="Sin verificación externa"),
            sa.Column("inventory_owner", sa.String(length=160), nullable=False, server_default=""),
            sa.Column("executive_sponsor", sa.String(length=160), nullable=False, server_default=""),
            sa.Column("profile_completion", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="Borrador"),
            sa.Column("source", sa.String(length=80), nullable=False, server_default="Configuración interna"),
            sa.Column("updated_by", sa.String(length=180), nullable=False, server_default="sistema"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("organization_id", name="uq_carbon_profile_organization"),
        )
        op.create_index("ix_carbon_profile_org", "organization_carbon_profiles", ["organization_id"])

    existing = _tables()
    if "diagnostic_assessments" not in existing:
        op.create_table(
            "diagnostic_assessments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
            sa.Column("lead_id", sa.Integer(), sa.ForeignKey("commercial_leads.id"), nullable=True),
            sa.Column("assessment_code", sa.String(length=80), nullable=False),
            sa.Column("assessment_version", sa.String(length=30), nullable=False, server_default="V0.45"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="Calculado"),
            sa.Column("company_size_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("operational_complexity_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("scope_complexity_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("data_maturity_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("governance_maturity_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("reporting_pressure_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("verification_readiness_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("maturity_level", sa.String(length=60), nullable=False, server_default="Inicial"),
            sa.Column("complexity_level", sa.String(length=60), nullable=False, server_default="Baja"),
            sa.Column("recommended_package_code", sa.String(length=40), nullable=False, server_default="ESENCIAL"),
            sa.Column("estimated_duration_months", sa.Integer(), nullable=False, server_default="2"),
            sa.Column("estimated_effort_hours", sa.Integer(), nullable=False, server_default="40"),
            sa.Column("recommended_scopes_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("applicable_modules_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("probable_sources_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("priority_scope3_categories_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("exclusions_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("findings_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("risk_flags_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("next_steps_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("answers_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("assessed_by", sa.String(length=180), nullable=False, server_default="motor-v045"),
            sa.Column("assessed_at", sa.DateTime(), nullable=False),
            sa.Column("approved_by", sa.String(length=180), nullable=False, server_default=""),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("approval_notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.UniqueConstraint("assessment_code", name="uq_diagnostic_assessment_code"),
        )
        op.create_index("ix_diagnostic_org", "diagnostic_assessments", ["organization_id"])
        op.create_index("ix_diagnostic_lead", "diagnostic_assessments", ["lead_id"])
        op.create_index("ix_diagnostic_code", "diagnostic_assessments", ["assessment_code"])

    existing = _tables()
    if "implementation_plans" not in existing:
        op.create_table(
            "implementation_plans",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("assessment_id", sa.Integer(), sa.ForeignKey("diagnostic_assessments.id"), nullable=False),
            sa.Column("code", sa.String(length=80), nullable=False),
            sa.Column("title", sa.String(length=220), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="Borrador"),
            sa.Column("package_code", sa.String(length=40), nullable=False, server_default="ESENCIAL"),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("target_completion", sa.Date(), nullable=True),
            sa.Column("duration_months", sa.Integer(), nullable=False, server_default="2"),
            sa.Column("scope_summary", sa.Text(), nullable=False, server_default=""),
            sa.Column("success_criteria_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("owner", sa.String(length=180), nullable=False, server_default="Equipo del inventario"),
            sa.Column("created_by", sa.String(length=180), nullable=False, server_default="sistema"),
            sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("code", name="uq_implementation_plan_code"),
        )
        op.create_index("ix_implementation_plan_org", "implementation_plans", ["organization_id"])
        op.create_index("ix_implementation_plan_assessment", "implementation_plans", ["assessment_id"])
        op.create_index("ix_implementation_plan_code", "implementation_plans", ["code"])

    existing = _tables()
    if "implementation_plan_items" not in existing:
        op.create_table(
            "implementation_plan_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("plan_id", sa.Integer(), sa.ForeignKey("implementation_plans.id"), nullable=False),
            sa.Column("phase_code", sa.String(length=40), nullable=False),
            sa.Column("phase_name", sa.String(length=120), nullable=False),
            sa.Column("title", sa.String(length=220), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="Pendiente"),
            sa.Column("owner", sa.String(length=180), nullable=False, server_default="Equipo del inventario"),
            sa.Column("due_date", sa.Date(), nullable=True),
            sa.Column("dependencies_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("deliverables_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("module_route", sa.String(length=240), nullable=False, server_default=""),
            sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("updated_by", sa.String(length=180), nullable=False, server_default="sistema"),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("plan_id", "phase_code", "title", name="uq_plan_phase_title"),
        )
        op.create_index("ix_implementation_item_plan", "implementation_plan_items", ["plan_id"])


def downgrade() -> None:
    existing = _tables()
    if "implementation_plan_items" in existing:
        op.drop_index("ix_implementation_item_plan", table_name="implementation_plan_items")
        op.drop_table("implementation_plan_items")
    if "implementation_plans" in existing:
        op.drop_index("ix_implementation_plan_code", table_name="implementation_plans")
        op.drop_index("ix_implementation_plan_assessment", table_name="implementation_plans")
        op.drop_index("ix_implementation_plan_org", table_name="implementation_plans")
        op.drop_table("implementation_plans")
    if "diagnostic_assessments" in existing:
        op.drop_index("ix_diagnostic_code", table_name="diagnostic_assessments")
        op.drop_index("ix_diagnostic_lead", table_name="diagnostic_assessments")
        op.drop_index("ix_diagnostic_org", table_name="diagnostic_assessments")
        op.drop_table("diagnostic_assessments")
    if "organization_carbon_profiles" in existing:
        op.drop_index("ix_carbon_profile_org", table_name="organization_carbon_profiles")
        op.drop_table("organization_carbon_profiles")
