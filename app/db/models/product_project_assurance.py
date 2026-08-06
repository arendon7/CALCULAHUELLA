from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base


class ProductFootprintStudy(Base):
    __tablename__ = "product_footprint_studies"

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventories.id"), index=True)
    product_name: Mapped[str] = mapped_column(String(180))
    product_code: Mapped[str] = mapped_column(String(80), default="")
    declared_unit: Mapped[str] = mapped_column(String(100))
    reference_flow: Mapped[float] = mapped_column(Float, default=1.0)
    boundary: Mapped[str] = mapped_column(String(60), default="De la cuna a la puerta")
    methodology: Mapped[str] = mapped_column(String(180), default="ISO 14067:2018")
    pcr_reference: Mapped[str] = mapped_column(String(240), default="")
    allocation_method: Mapped[str] = mapped_column(String(180), default="Sin asignación")
    cutoff_rule_percent: Mapped[float] = mapped_column(Float, default=1.0)
    biogenic_treatment: Mapped[str] = mapped_column(String(180), default="Reporte separado")
    land_use_included: Mapped[bool] = mapped_column(Boolean, default=False)
    data_quality_rating: Mapped[str] = mapped_column(String(20), default="C")
    status: Mapped[str] = mapped_column(String(30), default="Borrador")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(180), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    reviewed_by: Mapped[str] = mapped_column(String(180), default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    inventory: Mapped["Inventory"] = relationship()
    stages: Mapped[list["ProductLifeCycleStage"]] = relationship(back_populates="study", cascade="all, delete-orphan")


class ProductLifeCycleStage(Base):
    __tablename__ = "product_lifecycle_stages"

    id: Mapped[int] = mapped_column(primary_key=True)
    study_id: Mapped[int] = mapped_column(ForeignKey("product_footprint_studies.id"), index=True)
    stage_code: Mapped[str] = mapped_column(String(30))
    stage_name: Mapped[str] = mapped_column(String(120))
    accounting_type: Mapped[str] = mapped_column(String(40), default="Emisión")
    activity_name: Mapped[str] = mapped_column(String(180))
    activity_value: Mapped[float] = mapped_column(Float, default=0)
    activity_unit: Mapped[str] = mapped_column(String(40), default="unidad")
    factor_value: Mapped[float] = mapped_column(Float, default=0)
    factor_output_unit: Mapped[str] = mapped_column(String(40), default="kg CO2e")
    calculated_tco2e: Mapped[float] = mapped_column(Float, default=0)
    data_source: Mapped[str] = mapped_column(String(240), default="")
    geography: Mapped[str] = mapped_column(String(100), default="")
    reference_year: Mapped[int] = mapped_column(Integer, default=0)
    uncertainty_percentage: Mapped[float] = mapped_column(Float, default=0)
    evidence_reference: Mapped[str] = mapped_column(String(240), default="")
    excluded: Mapped[bool] = mapped_column(Boolean, default=False)
    exclusion_reason: Mapped[str] = mapped_column(String(280), default="")
    created_by: Mapped[str] = mapped_column(String(180), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    study: Mapped[ProductFootprintStudy] = relationship(back_populates="stages")


class MitigationProject(Base):
    __tablename__ = "mitigation_projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventories.id"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    project_type: Mapped[str] = mapped_column(String(100), default="Reducción de emisiones")
    methodology: Mapped[str] = mapped_column(String(220), default="ISO 14064-2:2019")
    baseline_scenario: Mapped[str] = mapped_column(Text)
    project_scenario: Mapped[str] = mapped_column(Text)
    additionality_basis: Mapped[str] = mapped_column(Text, default="")
    monitoring_plan: Mapped[str] = mapped_column(Text, default="")
    leakage_sources: Mapped[str] = mapped_column(Text, default="")
    ownership_statement: Mapped[str] = mapped_column(Text, default="")
    double_counting_control: Mapped[str] = mapped_column(Text, default="")
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    estimated_baseline_tco2e: Mapped[float] = mapped_column(Float, default=0)
    estimated_project_tco2e: Mapped[float] = mapped_column(Float, default=0)
    estimated_leakage_tco2e: Mapped[float] = mapped_column(Float, default=0)
    estimated_removals_tco2e: Mapped[float] = mapped_column(Float, default=0)
    estimated_reduction_tco2e: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(30), default="Diseño")
    created_by: Mapped[str] = mapped_column(String(180), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    reviewed_by: Mapped[str] = mapped_column(String(180), default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    inventory: Mapped["Inventory"] = relationship()
    monitoring_periods: Mapped[list["MitigationMonitoringPeriod"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class MitigationMonitoringPeriod(Base):
    __tablename__ = "mitigation_monitoring_periods"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("mitigation_projects.id"), index=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    baseline_tco2e: Mapped[float] = mapped_column(Float, default=0)
    project_tco2e: Mapped[float] = mapped_column(Float, default=0)
    leakage_tco2e: Mapped[float] = mapped_column(Float, default=0)
    removals_tco2e: Mapped[float] = mapped_column(Float, default=0)
    reduction_tco2e: Mapped[float] = mapped_column(Float, default=0)
    uncertainty_percentage: Mapped[float] = mapped_column(Float, default=0)
    evidence_reference: Mapped[str] = mapped_column(String(260), default="")
    status: Mapped[str] = mapped_column(String(30), default="Borrador")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(180), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    project: Mapped[MitigationProject] = relationship(back_populates="monitoring_periods")


class AssuranceEngagement(Base):
    __tablename__ = "assurance_engagements"

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventories.id"), index=True)
    subject_type: Mapped[str] = mapped_column(String(40), default="Inventario corporativo")
    subject_reference: Mapped[str] = mapped_column(String(120), default="")
    engagement_type: Mapped[str] = mapped_column(String(30), default="Verificación")
    standard: Mapped[str] = mapped_column(String(120), default="ISO 14064-3:2019")
    assurance_level: Mapped[str] = mapped_column(String(30), default="Limitado")
    materiality_percent: Mapped[float] = mapped_column(Float, default=5.0)
    criteria: Mapped[str] = mapped_column(Text)
    scope: Mapped[str] = mapped_column(Text)
    verifier_organization: Mapped[str] = mapped_column(String(180))
    lead_verifier: Mapped[str] = mapped_column(String(180))
    independence_declaration: Mapped[str] = mapped_column(Text, default="")
    competence_basis: Mapped[str] = mapped_column(Text, default="")
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="Planificado")
    conclusion: Mapped[str] = mapped_column(Text, default="")
    opinion: Mapped[str] = mapped_column(String(60), default="")
    statement_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by: Mapped[str] = mapped_column(String(180), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    inventory: Mapped["Inventory"] = relationship()
    findings: Mapped[list["AssuranceFinding"]] = relationship(back_populates="engagement", cascade="all, delete-orphan")


class AssuranceFinding(Base):
    __tablename__ = "assurance_findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("assurance_engagements.id"), index=True)
    area: Mapped[str] = mapped_column(String(120), default="General")
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(30), default="Menor")
    status: Mapped[str] = mapped_column(String(30), default="Abierto")
    evidence_reference: Mapped[str] = mapped_column(String(260), default="")
    management_response: Mapped[str] = mapped_column(Text, default="")
    verifier_conclusion: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(180), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    engagement: Mapped[AssuranceEngagement] = relationship(back_populates="findings")
