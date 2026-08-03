from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base


class OrganizationCarbonProfile(Base):
    __tablename__ = "organization_carbon_profiles"
    __table_args__ = (UniqueConstraint("organization_id", name="uq_carbon_profile_organization"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    company_size: Mapped[str] = mapped_column(String(40), default="Por definir")
    business_model: Mapped[str] = mapped_column(String(160), default="")
    sector_subsector: Mapped[str] = mapped_column(String(180), default="")
    operating_description: Mapped[str] = mapped_column(Text, default="")
    countries_count: Mapped[int] = mapped_column(Integer, default=1)
    countries_json: Mapped[str] = mapped_column(Text, default="[]")
    facility_types_json: Mapped[str] = mapped_column(Text, default="[]")
    core_processes_json: Mapped[str] = mapped_column(Text, default="[]")
    energy_sources_json: Mapped[str] = mapped_column(Text, default="[]")
    fleet_profile: Mapped[str] = mapped_column(Text, default="")
    refrigerants_profile: Mapped[str] = mapped_column(Text, default="")
    waste_profile: Mapped[str] = mapped_column(Text, default="")
    wastewater_profile: Mapped[str] = mapped_column(Text, default="")
    agriculture_land_use_profile: Mapped[str] = mapped_column(Text, default="")
    key_materials_json: Mapped[str] = mapped_column(Text, default="[]")
    supplier_profile: Mapped[str] = mapped_column(Text, default="")
    reporting_drivers_json: Mapped[str] = mapped_column(Text, default="[]")
    climate_goals_json: Mapped[str] = mapped_column(Text, default="[]")
    current_data_systems_json: Mapped[str] = mapped_column(Text, default="[]")
    inventory_history: Mapped[str] = mapped_column(String(80), default="Sin inventario anterior")
    data_availability: Mapped[str] = mapped_column(String(60), default="Baja")
    evidence_readiness: Mapped[str] = mapped_column(String(60), default="Baja")
    reporting_frequency: Mapped[str] = mapped_column(String(40), default="Anual")
    assurance_ambition: Mapped[str] = mapped_column(String(80), default="Sin verificación externa")
    inventory_owner: Mapped[str] = mapped_column(String(160), default="")
    executive_sponsor: Mapped[str] = mapped_column(String(160), default="")
    profile_completion: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="Borrador")
    source: Mapped[str] = mapped_column(String(80), default="Configuración interna")
    updated_by: Mapped[str] = mapped_column(String(180), default="sistema")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    organization: Mapped["Organization"] = relationship()


class DiagnosticAssessment(Base):
    __tablename__ = "diagnostic_assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("commercial_leads.id"), nullable=True, index=True)
    assessment_code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    assessment_version: Mapped[str] = mapped_column(String(30), default="V0.45")
    status: Mapped[str] = mapped_column(String(30), default="Calculado")
    company_size_score: Mapped[int] = mapped_column(Integer, default=0)
    operational_complexity_score: Mapped[int] = mapped_column(Integer, default=0)
    scope_complexity_score: Mapped[int] = mapped_column(Integer, default=0)
    data_maturity_score: Mapped[int] = mapped_column(Integer, default=0)
    governance_maturity_score: Mapped[int] = mapped_column(Integer, default=0)
    reporting_pressure_score: Mapped[int] = mapped_column(Integer, default=0)
    verification_readiness_score: Mapped[int] = mapped_column(Integer, default=0)
    total_score: Mapped[int] = mapped_column(Integer, default=0)
    maturity_level: Mapped[str] = mapped_column(String(60), default="Inicial")
    complexity_level: Mapped[str] = mapped_column(String(60), default="Baja")
    recommended_package_code: Mapped[str] = mapped_column(String(40), default="ESENCIAL")
    estimated_duration_months: Mapped[int] = mapped_column(Integer, default=2)
    estimated_effort_hours: Mapped[int] = mapped_column(Integer, default=40)
    recommended_scopes_json: Mapped[str] = mapped_column(Text, default="[]")
    applicable_modules_json: Mapped[str] = mapped_column(Text, default="[]")
    probable_sources_json: Mapped[str] = mapped_column(Text, default="[]")
    priority_scope3_categories_json: Mapped[str] = mapped_column(Text, default="[]")
    exclusions_json: Mapped[str] = mapped_column(Text, default="[]")
    findings_json: Mapped[str] = mapped_column(Text, default="[]")
    risk_flags_json: Mapped[str] = mapped_column(Text, default="[]")
    next_steps_json: Mapped[str] = mapped_column(Text, default="[]")
    answers_json: Mapped[str] = mapped_column(Text, default="{}")
    assessed_by: Mapped[str] = mapped_column(String(180), default="motor-v045")
    assessed_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    approved_by: Mapped[str] = mapped_column(String(180), default="")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approval_notes: Mapped[str] = mapped_column(Text, default="")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    organization: Mapped["Organization | None"] = relationship()
    lead: Mapped["CommercialLead | None"] = relationship()
    plans: Mapped[list["ImplementationPlan"]] = relationship(back_populates="assessment", cascade="all, delete-orphan")


class ImplementationPlan(Base):
    __tablename__ = "implementation_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("diagnostic_assessments.id"), index=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(220))
    status: Mapped[str] = mapped_column(String(30), default="Borrador")
    package_code: Mapped[str] = mapped_column(String(40), default="ESENCIAL")
    start_date: Mapped[date] = mapped_column(Date, default=date.today)
    target_completion: Mapped[date | None] = mapped_column(Date, nullable=True)
    duration_months: Mapped[int] = mapped_column(Integer, default=2)
    scope_summary: Mapped[str] = mapped_column(Text, default="")
    success_criteria_json: Mapped[str] = mapped_column(Text, default="[]")
    owner: Mapped[str] = mapped_column(String(180), default="Equipo del inventario")
    created_by: Mapped[str] = mapped_column(String(180), default="sistema")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    organization: Mapped["Organization"] = relationship()
    assessment: Mapped[DiagnosticAssessment] = relationship(back_populates="plans")
    items: Mapped[list["ImplementationPlanItem"]] = relationship(back_populates="plan", cascade="all, delete-orphan", order_by="ImplementationPlanItem.display_order")


class ImplementationPlanItem(Base):
    __tablename__ = "implementation_plan_items"
    __table_args__ = (UniqueConstraint("plan_id", "phase_code", "title", name="uq_plan_phase_title"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("implementation_plans.id"), index=True)
    phase_code: Mapped[str] = mapped_column(String(40))
    phase_name: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(220))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="Pendiente")
    owner: Mapped[str] = mapped_column(String(180), default="Equipo del inventario")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    dependencies_json: Mapped[str] = mapped_column(Text, default="[]")
    deliverables_json: Mapped[str] = mapped_column(Text, default="[]")
    module_route: Mapped[str] = mapped_column(String(240), default="")
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_by: Mapped[str] = mapped_column(String(180), default="sistema")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    plan: Mapped[ImplementationPlan] = relationship(back_populates="items")
