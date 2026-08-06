from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base

class UnitDefinition(Base):
    __tablename__ = "unit_definitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    dimension: Mapped[str] = mapped_column(String(50))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class UnitConversion(Base):
    __tablename__ = "unit_conversions"
    __table_args__ = (UniqueConstraint("from_unit", "to_unit", name="uq_unit_conversion"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    from_unit: Mapped[str] = mapped_column(String(30))
    to_unit: Mapped[str] = mapped_column(String(30))
    multiplier: Mapped[float] = mapped_column(Float)
    offset: Mapped[float] = mapped_column(Float, default=0)
    source: Mapped[str] = mapped_column(String(180), default="Conversión estándar")
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Gas(Base):
    __tablename__ = "gases"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    formula: Mapped[str] = mapped_column(String(40), default="")

    gwp_values: Mapped[list["GWPValue"]] = relationship(back_populates="gas", cascade="all, delete-orphan")
    factor_versions: Mapped[list["EmissionFactorVersion"]] = relationship(back_populates="gas")

class GWPValue(Base):
    __tablename__ = "gwp_values"
    __table_args__ = (UniqueConstraint("gas_id", "assessment", "horizon_years", name="uq_gwp_value"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    gas_id: Mapped[int] = mapped_column(ForeignKey("gases.id"))
    assessment: Mapped[str] = mapped_column(String(30))
    horizon_years: Mapped[int] = mapped_column(Integer, default=100)
    value: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(180), default="IPCC")
    status: Mapped[str] = mapped_column(String(30), default="Aprobado")

    gas: Mapped[Gas] = relationship(back_populates="gwp_values")

class EmissionFactor(Base):
    __tablename__ = "emission_factors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(180), unique=True)
    activity_type: Mapped[str] = mapped_column(String(120))
    country: Mapped[str] = mapped_column(String(80), default="Colombia")
    sector: Mapped[str] = mapped_column(String(100), default="Multisectorial")
    status: Mapped[str] = mapped_column(String(30), default="Activo")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    versions: Mapped[list["EmissionFactorVersion"]] = relationship(back_populates="factor", cascade="all, delete-orphan")

class EmissionFactorVersion(Base):
    __tablename__ = "emission_factor_versions"
    __table_args__ = (UniqueConstraint("factor_id", "version", "gas_id", name="uq_factor_version_gas"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    factor_id: Mapped[int] = mapped_column(ForeignKey("emission_factors.id"))
    gas_id: Mapped[int] = mapped_column(ForeignKey("gases.id"))
    version: Mapped[str] = mapped_column(String(30), default="1.0")
    value: Mapped[float] = mapped_column(Float)
    input_unit: Mapped[str] = mapped_column(String(30))
    output_unit: Mapped[str] = mapped_column(String(40), default="kg gas")
    source_organization: Mapped[str] = mapped_column(String(180), default="Biblioteca demostrativa")
    source_document: Mapped[str] = mapped_column(String(240), default="")
    publication_year: Mapped[int] = mapped_column(Integer, default=2025)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    geographic_scope: Mapped[str] = mapped_column(String(120), default="Colombia")
    technology_scope: Mapped[str] = mapped_column(String(160), default="Genérico")
    uncertainty_percentage: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(30), default="Aprobado")
    notes: Mapped[str] = mapped_column(Text, default="")
    approved_by: Mapped[str] = mapped_column(String(180), default="Comité metodológico demo")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    factor: Mapped[EmissionFactor] = relationship(back_populates="versions")
    gas: Mapped[Gas] = relationship(back_populates="factor_versions")
    assignments: Mapped[list["SourceFactorAssignment"]] = relationship(back_populates="factor_version")
    calculations: Mapped[list["EmissionCalculation"]] = relationship(back_populates="factor_version")

class SourceFactorAssignment(Base):
    __tablename__ = "source_factor_assignments"
    __table_args__ = (UniqueConstraint("source_id", "factor_version_id", name="uq_source_factor_assignment"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("emission_sources.id"))
    factor_version_id: Mapped[int] = mapped_column(ForeignKey("emission_factor_versions.id"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    assigned_by: Mapped[str] = mapped_column(String(180), default="sistema")
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    notes: Mapped[str] = mapped_column(Text, default="")

    source: Mapped[EmissionSource] = relationship(back_populates="factor_assignments")
    factor_version: Mapped[EmissionFactorVersion] = relationship(back_populates="assignments")


class ActivityFactorSelection(Base):
    """Selección metodológica específica para un dato de actividad.

    Permite que un mismo dato converse con uno o varios factores aprobados.
    Cuando existen selecciones activas, reemplazan los factores por defecto de la fuente
    únicamente para ese registro.
    """
    __tablename__ = "activity_factor_selections"
    __table_args__ = (UniqueConstraint("activity_data_id", "factor_version_id", name="uq_activity_factor_selection"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_data_id: Mapped[int] = mapped_column(ForeignKey("activity_data.id"), index=True)
    factor_version_id: Mapped[int] = mapped_column(ForeignKey("emission_factor_versions.id"), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    compatibility_score: Mapped[int] = mapped_column(Integer, default=0)
    selection_status: Mapped[str] = mapped_column(String(30), default="Seleccionado")
    rationale: Mapped[str] = mapped_column(Text, default="")
    selected_by: Mapped[str] = mapped_column(String(180), default="sistema")
    selected_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    reviewed_by: Mapped[str] = mapped_column(String(180), default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    review_notes: Mapped[str] = mapped_column(Text, default="")
    decision_snapshot: Mapped[str] = mapped_column(Text, default="{}")
    applied_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    activity_data: Mapped[ActivityData] = relationship(back_populates="factor_selections")
    factor_version: Mapped[EmissionFactorVersion] = relationship()

class EmissionCalculation(Base):
    __tablename__ = "emission_calculations"

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_data_id: Mapped[int] = mapped_column(ForeignKey("activity_data.id"))
    factor_version_id: Mapped[int] = mapped_column(ForeignKey("emission_factor_versions.id"))
    engine_version: Mapped[str] = mapped_column(String(30), default="0.4.0")
    original_value: Mapped[float] = mapped_column(Float)
    original_unit: Mapped[str] = mapped_column(String(30))
    normalized_value: Mapped[float] = mapped_column(Float, default=0)
    normalized_unit: Mapped[str] = mapped_column(String(30), default="")
    factor_value: Mapped[float] = mapped_column(Float)
    gas_code: Mapped[str] = mapped_column(String(30))
    gas_result_kg: Mapped[float] = mapped_column(Float, default=0)
    gwp_value: Mapped[float] = mapped_column(Float, default=1)
    co2e_kg: Mapped[float] = mapped_column(Float, default=0)
    reporting_bucket: Mapped[str] = mapped_column(String(40), default="Emisión bruta")
    uncertainty_percentage: Mapped[float] = mapped_column(Float, default=0)
    lower_co2e_kg: Mapped[float] = mapped_column(Float, default=0)
    upper_co2e_kg: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(30), default="Calculado")
    warning: Mapped[str] = mapped_column(Text, default="")
    formula_snapshot: Mapped[str] = mapped_column(Text, default="")
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    activity_data: Mapped[ActivityData] = relationship(back_populates="calculations")
    factor_version: Mapped[EmissionFactorVersion] = relationship(back_populates="calculations")

class MethodologyRelease(Base):
    __tablename__ = "methodology_releases"
    __table_args__ = (UniqueConstraint("organization_id", "name", "version", name="uq_methodology_release_org_name_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    version: Mapped[str] = mapped_column(String(60))
    issuing_body: Mapped[str] = mapped_column(String(160), default="")
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="Borrador")
    source_reference: Mapped[str] = mapped_column(String(300), default="")
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    approved_by: Mapped[str] = mapped_column(String(180), default="")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship()
    snapshots: Mapped[list["InventoryMethodologySnapshot"]] = relationship(back_populates="release")

class InventoryMethodologySnapshot(Base):
    __tablename__ = "inventory_methodology_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventories.id"), index=True)
    methodology_release_id: Mapped[int | None] = mapped_column(ForeignKey("methodology_releases.id"), nullable=True)
    snapshot_name: Mapped[str] = mapped_column(String(180))
    status: Mapped[str] = mapped_column(String(30), default="Borrador")
    methodology_name: Mapped[str] = mapped_column(String(180))
    methodology_version: Mapped[str] = mapped_column(String(180))
    gwp_version: Mapped[str] = mapped_column(String(100))
    consolidation_approach: Mapped[str] = mapped_column(String(100))
    materiality_threshold: Mapped[float] = mapped_column(Float, default=5.0)
    policy_json: Mapped[str] = mapped_column(Text, default="{}")
    approved_by: Mapped[str] = mapped_column(String(180), default="")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    inventory: Mapped[Inventory] = relationship()
    release: Mapped[MethodologyRelease | None] = relationship(back_populates="snapshots")

class BaseYearRecalculation(Base):
    __tablename__ = "base_year_recalculations"

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventories.id"), index=True)
    event_date: Mapped[date] = mapped_column(Date, default=date.today)
    trigger_type: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    previous_total_tco2e: Mapped[float] = mapped_column(Float, default=0)
    recalculated_total_tco2e: Mapped[float] = mapped_column(Float, default=0)
    change_percentage: Mapped[float] = mapped_column(Float, default=0)
    threshold_percentage: Mapped[float] = mapped_column(Float, default=5.0)
    decision: Mapped[str] = mapped_column(String(40), default="Evaluar")
    status: Mapped[str] = mapped_column(String(30), default="Pendiente")
    requested_by: Mapped[str] = mapped_column(String(180), default="")
    reviewed_by: Mapped[str] = mapped_column(String(180), default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    inventory: Mapped[Inventory] = relationship(back_populates="base_year_recalculations")

class ComplianceRequirement(Base):
    __tablename__ = "compliance_requirements"

    id: Mapped[int] = mapped_column(primary_key=True)
    framework: Mapped[str] = mapped_column(String(100), index=True)
    code: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(220))
    description: Mapped[str] = mapped_column(Text, default="")
    evidence_expected: Mapped[str] = mapped_column(Text, default="")
    mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    assessments: Mapped[list["ComplianceAssessment"]] = relationship(back_populates="requirement", cascade="all, delete-orphan")

class ComplianceAssessment(Base):
    __tablename__ = "compliance_assessments"
    __table_args__ = (UniqueConstraint("inventory_id", "requirement_id", name="uq_compliance_inventory_requirement"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventories.id"), index=True)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("compliance_requirements.id"), index=True)
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence_documents.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="Pendiente")
    owner: Mapped[str] = mapped_column(String(140), default="Responsable ambiental")
    notes: Mapped[str] = mapped_column(Text, default="")
    updated_by: Mapped[str] = mapped_column(String(180), default="sistema")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    inventory: Mapped[Inventory] = relationship()
    requirement: Mapped[ComplianceRequirement] = relationship(back_populates="assessments")
    evidence: Mapped[EvidenceDocument | None] = relationship()

class DocumentControlRecord(Base):
    __tablename__ = "document_control_records"
    __table_args__ = (UniqueConstraint("organization_id", "document_code", name="uq_document_control_org_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    inventory_id: Mapped[int | None] = mapped_column(ForeignKey("inventories.id"), nullable=True, index=True)
    evidence_document_id: Mapped[int | None] = mapped_column(ForeignKey("evidence_documents.id"), nullable=True)
    report_artifact_id: Mapped[int | None] = mapped_column(ForeignKey("report_artifacts.id"), nullable=True)
    document_code: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(220))
    category: Mapped[str] = mapped_column(String(100), default="Soporte")
    version: Mapped[str] = mapped_column(String(30), default="1.0")
    owner: Mapped[str] = mapped_column(String(140), default="Gestión ambiental")
    confidentiality: Mapped[str] = mapped_column(String(30), default="Interno")
    retention_years: Mapped[int] = mapped_column(Integer, default=7)
    review_due: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="Vigente")
    sha256: Mapped[str] = mapped_column(String(64), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(180), default="sistema")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship()
    inventory: Mapped[Inventory | None] = relationship()
    evidence: Mapped[EvidenceDocument | None] = relationship()
    report: Mapped[ReportArtifact | None] = relationship()
