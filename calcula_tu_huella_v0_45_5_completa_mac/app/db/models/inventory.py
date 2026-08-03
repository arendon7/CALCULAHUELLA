from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base

class Inventory(Base):
    __tablename__ = "inventories"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    name: Mapped[str] = mapped_column(String(120))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    objective: Mapped[str] = mapped_column(String(220), default="Inventario corporativo anual")
    base_year: Mapped[int] = mapped_column(Integer)
    methodology: Mapped[str] = mapped_column(String(120))
    methodology_version: Mapped[str] = mapped_column(String(120), default="GHG Protocol Corporate Standard")
    gwp_version: Mapped[str] = mapped_column(String(80), default="IPCC AR6 · 100 años")
    consolidation_approach: Mapped[str] = mapped_column(String(60), default="Control operacional")
    materiality_threshold: Mapped[float] = mapped_column(Float, default=5.0)
    status: Mapped[str] = mapped_column(String(40), default="Borrador")
    progress: Mapped[int] = mapped_column(Integer, default=10)
    current_stage: Mapped[str] = mapped_column(String(40), default="Configuración")
    notes: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[str] = mapped_column(String(20), default="0.5")
    parent_inventory_id: Mapped[int | None] = mapped_column(ForeignKey("inventories.id"), nullable=True)
    locked: Mapped[bool] = mapped_column(Boolean, default=False)
    submitted_for_review_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    submitted_for_review_by: Mapped[str] = mapped_column(String(180), default="")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approved_by: Mapped[str] = mapped_column(String(180), default="")
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_by: Mapped[str] = mapped_column(String(180), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship(back_populates="inventories")
    sources: Mapped[list["EmissionSource"]] = relationship(back_populates="inventory", cascade="all, delete-orphan")
    facility_links: Mapped[list["InventoryFacility"]] = relationship(back_populates="inventory", cascade="all, delete-orphan")
    requests: Mapped[list["DataRequest"]] = relationship(back_populates="inventory", cascade="all, delete-orphan")
    documents: Mapped[list["EvidenceDocument"]] = relationship(back_populates="inventory", cascade="all, delete-orphan")
    observations: Mapped[list["ReviewObservation"]] = relationship(back_populates="inventory", cascade="all, delete-orphan")
    decisions: Mapped[list["InventoryDecision"]] = relationship(back_populates="inventory", cascade="all, delete-orphan")
    indicators: Mapped[list["ActivityIndicator"]] = relationship(back_populates="inventory", cascade="all, delete-orphan")
    reduction_actions: Mapped[list["ReductionAction"]] = relationship(back_populates="inventory", cascade="all, delete-orphan")
    reports: Mapped[list["ReportArtifact"]] = relationship(back_populates="inventory", cascade="all, delete-orphan")
    targets: Mapped[list["EmissionTarget"]] = relationship(back_populates="inventory", cascade="all, delete-orphan")
    reduction_scenarios: Mapped[list["ReductionScenario"]] = relationship(back_populates="inventory", cascade="all, delete-orphan")
    verification_findings: Mapped[list["VerificationFinding"]] = relationship(back_populates="inventory", cascade="all, delete-orphan")
    supplier_campaigns: Mapped[list["SupplierCampaign"]] = relationship(back_populates="inventory", cascade="all, delete-orphan")
    base_year_recalculations: Mapped[list["BaseYearRecalculation"]] = relationship(back_populates="inventory", cascade="all, delete-orphan")

class InventoryFacility(Base):
    __tablename__ = "inventory_facilities"

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventories.id"))
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"))
    included: Mapped[bool] = mapped_column(Boolean, default=True)
    inclusion_percentage: Mapped[float] = mapped_column(Float, default=100)
    exclusion_reason: Mapped[str] = mapped_column(String(250), default="")

    inventory: Mapped[Inventory] = relationship(back_populates="facility_links")
    facility: Mapped[Facility] = relationship(back_populates="inventory_links")

class EmissionSource(Base):
    __tablename__ = "emission_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventories.id"))
    facility_id: Mapped[int | None] = mapped_column(ForeignKey("facilities.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(100))
    scope: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(120))
    responsible: Mapped[str] = mapped_column(String(120), default="Responsable ambiental")
    materiality: Mapped[str] = mapped_column(String(30), default="Media")
    data_frequency: Mapped[str] = mapped_column(String(30), default="Mensual")
    preferred_unit: Mapped[str] = mapped_column(String(30), default="")
    included: Mapped[bool] = mapped_column(Boolean, default=True)
    exclusion_reason: Mapped[str] = mapped_column(String(250), default="")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(40), default="Pendiente")
    accounting_treatment: Mapped[str] = mapped_column(String(40), default="Emisión bruta")
    scope2_method: Mapped[str] = mapped_column(String(30), default="No aplica")
    biogenic_origin: Mapped[str] = mapped_column(String(80), default="No aplica")
    emissions: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str] = mapped_column(String(30), default="tCO₂e")
    icon: Mapped[str] = mapped_column(String(30), default="activity")

    inventory: Mapped[Inventory] = relationship(back_populates="sources")
    facility: Mapped[Facility | None] = relationship(back_populates="source_records")
    activity_records: Mapped[list["ActivityData"]] = relationship(back_populates="source", cascade="all, delete-orphan")
    evidence_documents: Mapped[list["EvidenceDocument"]] = relationship(back_populates="source")
    requests: Mapped[list["DataRequest"]] = relationship(back_populates="source")
    factor_assignments: Mapped[list["SourceFactorAssignment"]] = relationship(back_populates="source", cascade="all, delete-orphan")
    reduction_actions: Mapped[list["ReductionAction"]] = relationship(back_populates="source")

class EvidenceDocument(Base):
    __tablename__ = "evidence_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventories.id"))
    source_id: Mapped[int | None] = mapped_column(ForeignKey("emission_sources.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(180))
    stored_name: Mapped[str] = mapped_column(String(220), default="")
    document_type: Mapped[str] = mapped_column(String(80))
    source_name: Mapped[str] = mapped_column(String(120), default="")
    period_label: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(40), default="Cargado")
    uploaded_by: Mapped[str] = mapped_column(String(120))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str] = mapped_column(String(64), default="")
    notes: Mapped[str] = mapped_column(Text, default="")

    inventory: Mapped[Inventory] = relationship(back_populates="documents")
    source: Mapped[EmissionSource | None] = relationship(back_populates="evidence_documents")
    activity_records: Mapped[list["ActivityData"]] = relationship(back_populates="evidence")

class ActivityData(Base):
    __tablename__ = "activity_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("emission_sources.id"))
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence_documents.id"), nullable=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(30))
    data_origin: Mapped[str] = mapped_column(String(80), default="Registro operativo")
    quality_level: Mapped[str] = mapped_column(String(20), default="B")
    is_estimated: Mapped[bool] = mapped_column(Boolean, default=False)
    uncertainty_percentage: Mapped[float] = mapped_column(Float, default=0)
    uncertainty_basis: Mapped[str] = mapped_column(String(180), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="Cargado")
    created_by: Mapped[str] = mapped_column(String(180))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    source: Mapped[EmissionSource] = relationship(back_populates="activity_records")
    evidence: Mapped[EvidenceDocument | None] = relationship(back_populates="activity_records")
    calculations: Mapped[list["EmissionCalculation"]] = relationship(back_populates="activity_data", cascade="all, delete-orphan")

class DataRequest(Base):
    __tablename__ = "data_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventories.id"))
    source_id: Mapped[int | None] = mapped_column(ForeignKey("emission_sources.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(180))
    source_name: Mapped[str] = mapped_column(String(120), default="")
    requested_to: Mapped[str] = mapped_column(String(120))
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40), default="Pendiente")
    instructions: Mapped[str] = mapped_column(Text, default="")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    inventory: Mapped[Inventory] = relationship(back_populates="requests")
    source: Mapped[EmissionSource | None] = relationship(back_populates="requests")

class ReviewObservation(Base):
    __tablename__ = "review_observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventories.id"))
    source_id: Mapped[int | None] = mapped_column(ForeignKey("emission_sources.id"), nullable=True)
    activity_data_id: Mapped[int | None] = mapped_column(ForeignKey("activity_data.id"), nullable=True)
    factor_version_id: Mapped[int | None] = mapped_column(ForeignKey("emission_factor_versions.id"), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(60), default="Inventario")
    entity_label: Mapped[str] = mapped_column(String(180), default="")
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(30), default="Menor")
    status: Mapped[str] = mapped_column(String(40), default="Abierta")
    assigned_to: Mapped[str] = mapped_column(String(180), default="")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by: Mapped[str] = mapped_column(String(180))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    response: Mapped[str] = mapped_column(Text, default="")
    responded_by: Mapped[str] = mapped_column(String(180), default="")
    responded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolution: Mapped[str] = mapped_column(Text, default="")
    resolved_by: Mapped[str] = mapped_column(String(180), default="")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_by: Mapped[str] = mapped_column(String(180), default="")
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    inventory: Mapped[Inventory] = relationship(back_populates="observations")
    source: Mapped[EmissionSource | None] = relationship()
    activity_data: Mapped[ActivityData | None] = relationship()
    factor_version: Mapped["EmissionFactorVersion | None"] = relationship()

class InventoryDecision(Base):
    __tablename__ = "inventory_decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventories.id"))
    decision_type: Mapped[str] = mapped_column(String(60))
    decision: Mapped[str] = mapped_column(String(60))
    comments: Mapped[str] = mapped_column(Text, default="")
    decided_by: Mapped[str] = mapped_column(String(180))
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    inventory_version: Mapped[str] = mapped_column(String(20), default="")

    inventory: Mapped[Inventory] = relationship(back_populates="decisions")

class ActivityIndicator(Base):
    __tablename__ = "activity_indicators"

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventories.id"))
    facility_id: Mapped[int | None] = mapped_column(ForeignKey("facilities.id"), nullable=True)
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence_documents.id"), nullable=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    indicator_type: Mapped[str] = mapped_column(String(80))
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(40))
    source_name: Mapped[str] = mapped_column(String(120), default="Registro operativo")
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="Cargado")
    created_by: Mapped[str] = mapped_column(String(180))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    inventory: Mapped[Inventory] = relationship(back_populates="indicators")
    facility: Mapped[Facility | None] = relationship(back_populates="activity_indicators")
    evidence: Mapped[EvidenceDocument | None] = relationship()

class ReductionAction(Base):
    __tablename__ = "reduction_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventories.id"))
    source_id: Mapped[int | None] = mapped_column(ForeignKey("emission_sources.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text, default="")
    baseline_emissions: Mapped[float] = mapped_column(Float, default=0)
    expected_reduction: Mapped[float] = mapped_column(Float, default=0)
    investment_cost: Mapped[float] = mapped_column(Float, default=0)
    annual_savings: Mapped[float] = mapped_column(Float, default=0)
    priority: Mapped[str] = mapped_column(String(30), default="Media")
    responsible: Mapped[str] = mapped_column(String(120), default="")
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="Identificada")
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    actual_reduction: Mapped[float] = mapped_column(Float, default=0)
    actual_savings: Mapped[float] = mapped_column(Float, default=0)
    useful_life_years: Mapped[int] = mapped_column(Integer, default=5)
    implementation_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feasibility: Mapped[str] = mapped_column(String(30), default="Media")
    risk_level: Mapped[str] = mapped_column(String(30), default="Medio")
    created_by: Mapped[str] = mapped_column(String(180))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    inventory: Mapped[Inventory] = relationship(back_populates="reduction_actions")
    source: Mapped[EmissionSource | None] = relationship(back_populates="reduction_actions")

class ReportArtifact(Base):
    __tablename__ = "report_artifacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventories.id"))
    report_type: Mapped[str] = mapped_column(String(60))
    version: Mapped[str] = mapped_column(String(20), default="1.0")
    status: Mapped[str] = mapped_column(String(30), default="Generado")
    file_name: Mapped[str] = mapped_column(String(220))
    stored_name: Mapped[str] = mapped_column(String(260))
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str] = mapped_column(String(64), default="")
    generated_by: Mapped[str] = mapped_column(String(180))
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    approved_by: Mapped[str] = mapped_column(String(180), default="")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    inventory: Mapped[Inventory] = relationship(back_populates="reports")

class SectorTemplate(Base):
    __tablename__ = "sector_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    sector: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[str] = mapped_column(String(30), default="1.0")
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    source_items: Mapped[list["SectorTemplateSource"]] = relationship(back_populates="template", cascade="all, delete-orphan")

class SectorTemplateSource(Base):
    __tablename__ = "sector_template_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("sector_templates.id"))
    name: Mapped[str] = mapped_column(String(120))
    scope: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(Text, default="")
    data_frequency: Mapped[str] = mapped_column(String(30), default="Mensual")
    preferred_unit: Mapped[str] = mapped_column(String(30), default="")
    materiality: Mapped[str] = mapped_column(String(30), default="Media")
    responsible: Mapped[str] = mapped_column(String(120), default="Responsable ambiental")
    icon: Mapped[str] = mapped_column(String(30), default="activity")
    factor_activity_type: Mapped[str] = mapped_column(String(120), default="")
    recommended: Mapped[bool] = mapped_column(Boolean, default=True)

    template: Mapped[SectorTemplate] = relationship(back_populates="source_items")

class EmissionTarget(Base):
    __tablename__ = "emission_targets"

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventories.id"))
    name: Mapped[str] = mapped_column(String(180))
    metric_type: Mapped[str] = mapped_column(String(40), default="Absoluta")
    baseline_year: Mapped[int] = mapped_column(Integer)
    target_year: Mapped[int] = mapped_column(Integer)
    baseline_value: Mapped[float] = mapped_column(Float)
    target_value: Mapped[float] = mapped_column(Float)
    current_value: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str] = mapped_column(String(50), default="tCO₂e")
    status: Mapped[str] = mapped_column(String(40), default="Activa")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(180))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    inventory: Mapped[Inventory] = relationship(back_populates="targets")

    @property
    def reduction_percent(self) -> float:
        if not self.baseline_value:
            return 0
        return max(0.0, (self.baseline_value - self.target_value) / self.baseline_value * 100)

    @property
    def progress_percent(self) -> float:
        required = self.baseline_value - self.target_value
        achieved = self.baseline_value - self.current_value
        if required <= 0:
            return 0
        return max(0.0, min(100.0, achieved / required * 100))

class ReductionScenario(Base):
    __tablename__ = "reduction_scenarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventories.id"))
    name: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text, default="")
    start_year: Mapped[int] = mapped_column(Integer)
    target_year: Mapped[int] = mapped_column(Integer)
    discount_rate: Mapped[float] = mapped_column(Float, default=10.0)
    status: Mapped[str] = mapped_column(String(40), default="Borrador")
    created_by: Mapped[str] = mapped_column(String(180))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    inventory: Mapped[Inventory] = relationship(back_populates="reduction_scenarios")
    action_links: Mapped[list["ReductionScenarioAction"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")

class ReductionScenarioAction(Base):
    __tablename__ = "reduction_scenario_actions"
    __table_args__ = (UniqueConstraint("scenario_id", "action_id", name="uq_scenario_action"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("reduction_scenarios.id"))
    action_id: Mapped[int] = mapped_column(ForeignKey("reduction_actions.id"))
    included: Mapped[bool] = mapped_column(Boolean, default=True)
    implementation_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    adoption_percent: Mapped[float] = mapped_column(Float, default=100.0)

    scenario: Mapped[ReductionScenario] = relationship(back_populates="action_links")
    action: Mapped[ReductionAction] = relationship()

class VerificationFinding(Base):
    __tablename__ = "verification_findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventories.id"))
    source_id: Mapped[int | None] = mapped_column(ForeignKey("emission_sources.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    finding_type: Mapped[str] = mapped_column(String(50), default="Observación")
    severity: Mapped[str] = mapped_column(String(30), default="Menor")
    status: Mapped[str] = mapped_column(String(40), default="Abierto")
    verifier_email: Mapped[str] = mapped_column(String(180))
    management_response: Mapped[str] = mapped_column(Text, default="")
    response_by: Mapped[str] = mapped_column(String(180), default="")
    response_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    conclusion: Mapped[str] = mapped_column(Text, default="")
    closed_by: Mapped[str] = mapped_column(String(180), default="")
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    inventory: Mapped[Inventory] = relationship(back_populates="verification_findings")
    source: Mapped[EmissionSource | None] = relationship()
