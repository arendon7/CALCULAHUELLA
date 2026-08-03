from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base

class BenchmarkReference(Base):
    __tablename__ = "benchmark_references"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(220))
    sector: Mapped[str] = mapped_column(String(120), default="Multisectorial")
    metric_code: Mapped[str] = mapped_column(String(80), index=True)
    metric_name: Mapped[str] = mapped_column(String(180))
    period_label: Mapped[str] = mapped_column(String(60), default="Referencia")
    unit: Mapped[str] = mapped_column(String(60))
    median_value: Mapped[float] = mapped_column(Float, default=0)
    top_quartile_value: Mapped[float] = mapped_column(Float, default=0)
    lower_is_better: Mapped[bool] = mapped_column(Boolean, default=True)
    source_type: Mapped[str] = mapped_column(String(60), default="Referencia interna")
    source_reference: Mapped[str] = mapped_column(Text, default="")
    confidence_level: Mapped[str] = mapped_column(String(30), default="Media")
    status: Mapped[str] = mapped_column(String(30), default="Activo")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(180), default="sistema")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship()

class ImpactSnapshot(Base):
    __tablename__ = "impact_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    inventory_id: Mapped[int | None] = mapped_column(ForeignKey("inventories.id"), nullable=True, index=True)
    total_emissions: Mapped[float] = mapped_column(Float, default=0)
    intensity_employee: Mapped[float] = mapped_column(Float, default=0)
    intensity_revenue_billion: Mapped[float] = mapped_column(Float, default=0)
    intensity_production: Mapped[float] = mapped_column(Float, default=0)
    quality_score: Mapped[float] = mapped_column(Float, default=0)
    evidence_coverage: Mapped[float] = mapped_column(Float, default=0)
    expected_reduction: Mapped[float] = mapped_column(Float, default=0)
    actual_reduction: Mapped[float] = mapped_column(Float, default=0)
    investment: Mapped[float] = mapped_column(Float, default=0)
    annual_savings: Mapped[float] = mapped_column(Float, default=0)
    value_per_tonne: Mapped[float] = mapped_column(Float, default=0)
    impact_score: Mapped[int] = mapped_column(Integer, default=0)
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), index=True)
    created_by: Mapped[str] = mapped_column(String(180), default="sistema")

    organization: Mapped[Organization] = relationship()
    inventory: Mapped["Inventory | None"] = relationship()

class ClimateRiskAssessment(Base):
    __tablename__ = "climate_risk_assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    inventory_id: Mapped[int | None] = mapped_column(ForeignKey("inventories.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(220))
    methodology: Mapped[str] = mapped_column(String(180), default="Análisis corporativo de escenarios")
    scenario: Mapped[str] = mapped_column(String(120), default="Escenario central")
    base_year: Mapped[int] = mapped_column(Integer, default=2025)
    short_horizon: Mapped[int] = mapped_column(Integer, default=2027)
    medium_horizon: Mapped[int] = mapped_column(Integer, default=2030)
    long_horizon: Mapped[int] = mapped_column(Integer, default=2050)
    currency: Mapped[str] = mapped_column(String(20), default="COP")
    owner: Mapped[str] = mapped_column(String(180), default="Dirección ambiental")
    status: Mapped[str] = mapped_column(String(40), default="En evaluación")
    notes: Mapped[str] = mapped_column(Text, default="")
    reviewed_by: Mapped[str] = mapped_column(String(180), default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str] = mapped_column(String(180), default="sistema")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship()
    inventory: Mapped["Inventory | None"] = relationship()
    risks: Mapped[list["ClimateRisk"]] = relationship(back_populates="assessment", cascade="all, delete-orphan")
    roadmaps: Mapped[list["ClimateTransitionRoadmap"]] = relationship(back_populates="assessment", cascade="all, delete-orphan")

class ClimateRisk(Base):
    __tablename__ = "climate_risks"

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("climate_risk_assessments.id"), index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    risk_type: Mapped[str] = mapped_column(String(40), default="Físico")
    category: Mapped[str] = mapped_column(String(100), default="Crónico")
    hazard: Mapped[str] = mapped_column(String(220))
    description: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(String(180), default="Corporativo")
    value_chain_stage: Mapped[str] = mapped_column(String(100), default="Operación propia")
    time_horizon: Mapped[str] = mapped_column(String(40), default="Mediano plazo")
    scenario: Mapped[str] = mapped_column(String(120), default="Escenario central")
    likelihood: Mapped[int] = mapped_column(Integer, default=3)
    financial_impact: Mapped[int] = mapped_column(Integer, default=3)
    operational_impact: Mapped[int] = mapped_column(Integer, default=3)
    reputational_impact: Mapped[int] = mapped_column(Integer, default=2)
    inherent_score: Mapped[float] = mapped_column(Float, default=9)
    control_effectiveness: Mapped[int] = mapped_column(Integer, default=0)
    residual_score: Mapped[float] = mapped_column(Float, default=9)
    financial_exposure: Mapped[float] = mapped_column(Float, default=0)
    owner: Mapped[str] = mapped_column(String(180), default="Dirección ambiental")
    response_strategy: Mapped[str] = mapped_column(String(60), default="Mitigar")
    response_detail: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="Abierto")
    source_reference: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(180), default="sistema")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    assessment: Mapped[ClimateRiskAssessment] = relationship(back_populates="risks")
    organization: Mapped[Organization] = relationship()
    controls: Mapped[list["ClimateRiskControl"]] = relationship(back_populates="risk", cascade="all, delete-orphan")

class ClimateRiskControl(Base):
    __tablename__ = "climate_risk_controls"

    id: Mapped[int] = mapped_column(primary_key=True)
    risk_id: Mapped[int] = mapped_column(ForeignKey("climate_risks.id"), index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(220))
    control_type: Mapped[str] = mapped_column(String(80), default="Preventivo")
    owner: Mapped[str] = mapped_column(String(180), default="Operaciones")
    status: Mapped[str] = mapped_column(String(40), default="Diseñado")
    effectiveness: Mapped[int] = mapped_column(Integer, default=0)
    implementation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_review: Mapped[date | None] = mapped_column(Date, nullable=True)
    annual_cost: Mapped[float] = mapped_column(Float, default=0)
    evidence: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(180), default="sistema")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    risk: Mapped[ClimateRisk] = relationship(back_populates="controls")
    organization: Mapped[Organization] = relationship()

class ClimateTransitionRoadmap(Base):
    __tablename__ = "climate_transition_roadmaps"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    assessment_id: Mapped[int | None] = mapped_column(ForeignKey("climate_risk_assessments.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(220))
    baseline_year: Mapped[int] = mapped_column(Integer, default=2025)
    target_year: Mapped[int] = mapped_column(Integer, default=2030)
    owner: Mapped[str] = mapped_column(String(180), default="Comité climático")
    governance: Mapped[str] = mapped_column(Text, default="")
    approved_budget: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(40), default="Borrador")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(180), default="sistema")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship()
    assessment: Mapped["ClimateRiskAssessment | None"] = relationship(back_populates="roadmaps")
    actions: Mapped[list["ClimateTransitionAction"]] = relationship(back_populates="roadmap", cascade="all, delete-orphan")

class ClimateTransitionAction(Base):
    __tablename__ = "climate_transition_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    roadmap_id: Mapped[int] = mapped_column(ForeignKey("climate_transition_roadmaps.id"), index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    risk_id: Mapped[int | None] = mapped_column(ForeignKey("climate_risks.id"), nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(100), default="Descarbonización")
    title: Mapped[str] = mapped_column(String(220))
    description: Mapped[str] = mapped_column(Text, default="")
    owner: Mapped[str] = mapped_column(String(180), default="Dirección ambiental")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    priority: Mapped[str] = mapped_column(String(30), default="Media")
    status: Mapped[str] = mapped_column(String(40), default="Planeada")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    expected_reduction_tco2e: Mapped[float] = mapped_column(Float, default=0)
    capex: Mapped[float] = mapped_column(Float, default=0)
    annual_opex: Mapped[float] = mapped_column(Float, default=0)
    annual_savings: Mapped[float] = mapped_column(Float, default=0)
    avoided_loss: Mapped[float] = mapped_column(Float, default=0)
    indicator: Mapped[str] = mapped_column(String(180), default="")
    target_value: Mapped[float] = mapped_column(Float, default=0)
    current_value: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str] = mapped_column(String(60), default="")
    dependencies: Mapped[str] = mapped_column(Text, default="")
    evidence_note: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(180), default="sistema")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    roadmap: Mapped[ClimateTransitionRoadmap] = relationship(back_populates="actions")
    organization: Mapped[Organization] = relationship()
    risk: Mapped["ClimateRisk | None"] = relationship()

class ClimateScenarioDefinition(Base):
    __tablename__ = "climate_scenario_definitions"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_climate_scenario_org_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    assessment_id: Mapped[int | None] = mapped_column(ForeignKey("climate_risk_assessments.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(180))
    code: Mapped[str] = mapped_column(String(40), default="SCN")
    scenario_type: Mapped[str] = mapped_column(String(80), default="Escenario corporativo")
    temperature_pathway: Mapped[str] = mapped_column(String(80), default="No especificada")
    physical_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    transition_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    opportunity_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    carbon_price_2030: Mapped[float] = mapped_column(Float, default=0)
    energy_cost_change_pct: Mapped[float] = mapped_column(Float, default=0)
    demand_change_pct: Mapped[float] = mapped_column(Float, default=0)
    probability_weight: Mapped[float] = mapped_column(Float, default=0)
    narrative: Mapped[str] = mapped_column(Text, default="")
    source_reference: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="Activo")
    created_by: Mapped[str] = mapped_column(String(180), default="sistema")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship()
    assessment: Mapped["ClimateRiskAssessment | None"] = relationship()

class ClimateDisclosureStatement(Base):
    __tablename__ = "climate_disclosure_statements"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    inventory_id: Mapped[int | None] = mapped_column(ForeignKey("inventories.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(220))
    framework: Mapped[str] = mapped_column(String(180), default="Divulgación climática corporativa")
    reporting_period: Mapped[str] = mapped_column(String(80), default="2025")
    scope_description: Mapped[str] = mapped_column(Text, default="")
    materiality_basis: Mapped[str] = mapped_column(Text, default="")
    owner: Mapped[str] = mapped_column(String(180), default="Dirección ambiental")
    status: Mapped[str] = mapped_column(String(40), default="Borrador")
    approved_by: Mapped[str] = mapped_column(String(180), default="")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(180), default="sistema")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship()
    inventory: Mapped["Inventory | None"] = relationship()
    requirements: Mapped[list["ClimateDisclosureRequirement"]] = relationship(back_populates="statement", cascade="all, delete-orphan")

class ClimateDisclosureRequirement(Base):
    __tablename__ = "climate_disclosure_requirements"
    __table_args__ = (UniqueConstraint("statement_id", "code", name="uq_disclosure_statement_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    statement_id: Mapped[int] = mapped_column(ForeignKey("climate_disclosure_statements.id"), index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    pillar: Mapped[str] = mapped_column(String(80))
    code: Mapped[str] = mapped_column(String(40))
    requirement: Mapped[str] = mapped_column(Text)
    response: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="Pendiente")
    evidence_reference: Mapped[str] = mapped_column(Text, default="")
    owner: Mapped[str] = mapped_column(String(180), default="Dirección ambiental")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    updated_by: Mapped[str] = mapped_column(String(180), default="sistema")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    statement: Mapped[ClimateDisclosureStatement] = relationship(back_populates="requirements")
    organization: Mapped[Organization] = relationship()

class ClimateBoardBriefing(Base):
    __tablename__ = "climate_board_briefings"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    assessment_id: Mapped[int | None] = mapped_column(ForeignKey("climate_risk_assessments.id"), nullable=True, index=True)
    disclosure_id: Mapped[int | None] = mapped_column(ForeignKey("climate_disclosure_statements.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(220))
    meeting_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    audience: Mapped[str] = mapped_column(String(180), default="Comité directivo")
    status: Mapped[str] = mapped_column(String(40), default="Borrador")
    executive_summary: Mapped[str] = mapped_column(Text, default="")
    decisions_required: Mapped[str] = mapped_column(Text, default="")
    key_message: Mapped[str] = mapped_column(Text, default="")
    prepared_by: Mapped[str] = mapped_column(String(180), default="Dirección ambiental")
    approved_by: Mapped[str] = mapped_column(String(180), default="")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    document_hash: Mapped[str] = mapped_column(String(64), default="")
    created_by: Mapped[str] = mapped_column(String(180), default="sistema")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship()
    assessment: Mapped["ClimateRiskAssessment | None"] = relationship()
    disclosure: Mapped["ClimateDisclosureStatement | None"] = relationship()
    decisions: Mapped[list["ClimateBoardDecision"]] = relationship(back_populates="briefing", cascade="all, delete-orphan")

class ClimateBoardDecision(Base):
    __tablename__ = "climate_board_decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    briefing_id: Mapped[int] = mapped_column(ForeignKey("climate_board_briefings.id"), index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    topic: Mapped[str] = mapped_column(String(220))
    decision: Mapped[str] = mapped_column(Text, default="")
    owner: Mapped[str] = mapped_column(String(180), default="Gerencia")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="Pendiente")
    rationale: Mapped[str] = mapped_column(Text, default="")
    evidence_reference: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(180), default="sistema")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    briefing: Mapped[ClimateBoardBriefing] = relationship(back_populates="decisions")
    organization: Mapped[Organization] = relationship()
