from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base

class PilotProject(Base):
    __tablename__ = "pilot_projects"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_pilot_project_org_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    code: Mapped[str] = mapped_column(String(60))
    name: Mapped[str] = mapped_column(String(220))
    reporting_year: Mapped[int] = mapped_column(Integer, default=2026)
    consolidation_approach: Mapped[str] = mapped_column(String(100), default="Control operacional")
    organizational_boundary: Mapped[str] = mapped_column(Text, default="")
    operational_boundary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="Preparación")
    lead: Mapped[str] = mapped_column(String(180), default="Dirección ambiental")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship()
    requirements: Mapped[list["PilotSourceRequirement"]] = relationship(back_populates="pilot", cascade="all, delete-orphan")

class PilotSourceRequirement(Base):
    __tablename__ = "pilot_source_requirements"
    __table_args__ = (UniqueConstraint("pilot_id", "code", name="uq_pilot_requirement_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    pilot_id: Mapped[int] = mapped_column(ForeignKey("pilot_projects.id"), index=True)
    code: Mapped[str] = mapped_column(String(60))
    site: Mapped[str] = mapped_column(String(120))
    scope: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(120))
    source_name: Mapped[str] = mapped_column(String(220))
    activity_unit: Mapped[str] = mapped_column(String(40))
    frequency: Mapped[str] = mapped_column(String(40), default="Mensual")
    data_owner: Mapped[str] = mapped_column(String(180), default="Por asignar")
    evidence_expected: Mapped[str] = mapped_column(Text, default="")
    factor_status: Mapped[str] = mapped_column(String(60), default="Pendiente")
    factor_reference: Mapped[str] = mapped_column(String(220), default="")
    materiality: Mapped[str] = mapped_column(String(30), default="Media")
    status: Mapped[str] = mapped_column(String(40), default="Pendiente")
    notes: Mapped[str] = mapped_column(Text, default="")
    updated_by: Mapped[str] = mapped_column(String(180), default="sistema")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    pilot: Mapped[PilotProject] = relationship(back_populates="requirements")

class PilotExecution(Base):
    __tablename__ = "pilot_executions"
    __table_args__ = (UniqueConstraint("pilot_id", name="uq_pilot_execution_pilot"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    pilot_id: Mapped[int] = mapped_column(ForeignKey("pilot_projects.id"), index=True)
    inventory_id: Mapped[int | None] = mapped_column(ForeignKey("inventories.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(40), default="No iniciado")
    started_by: Mapped[str] = mapped_column(String(180), default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    platform_total_tco2e: Mapped[float] = mapped_column(Float, default=0)
    independent_total_tco2e: Mapped[float | None] = mapped_column(Float, nullable=True)
    variance_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    comparison_status: Mapped[str] = mapped_column(String(40), default="Pendiente")
    comparison_notes: Mapped[str] = mapped_column(Text, default="")
    approved_by: Mapped[str] = mapped_column(String(180), default="")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    pilot: Mapped[PilotProject] = relationship()
    inventory: Mapped[Inventory | None] = relationship()
    source_links: Mapped[list["PilotExecutionSourceLink"]] = relationship(back_populates="execution", cascade="all, delete-orphan")
    issues: Mapped[list["PilotIssue"]] = relationship(back_populates="execution", cascade="all, delete-orphan")
    comparisons: Mapped[list["PilotSourceComparison"]] = relationship(back_populates="execution", cascade="all, delete-orphan")

class PilotExecutionSourceLink(Base):
    __tablename__ = "pilot_execution_source_links"
    __table_args__ = (UniqueConstraint("execution_id", "requirement_id", name="uq_pilot_execution_requirement"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    execution_id: Mapped[int] = mapped_column(ForeignKey("pilot_executions.id"), index=True)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("pilot_source_requirements.id"), index=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("emission_sources.id"), nullable=True, index=True)
    request_id: Mapped[int | None] = mapped_column(ForeignKey("data_requests.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    execution: Mapped[PilotExecution] = relationship(back_populates="source_links")
    requirement: Mapped[PilotSourceRequirement] = relationship()
    source: Mapped[EmissionSource | None] = relationship()
    request: Mapped[DataRequest | None] = relationship()

class PilotIssue(Base):
    __tablename__ = "pilot_issues"
    __table_args__ = (UniqueConstraint("execution_id", "code", name="uq_pilot_issue_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    execution_id: Mapped[int] = mapped_column(ForeignKey("pilot_executions.id"), index=True)
    code: Mapped[str] = mapped_column(String(60))
    category: Mapped[str] = mapped_column(String(80), default="Datos")
    title: Mapped[str] = mapped_column(String(220))
    description: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(30), default="Media")
    status: Mapped[str] = mapped_column(String(40), default="Abierto")
    owner: Mapped[str] = mapped_column(String(180), default="Equipo piloto")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    resolution: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(180), default="sistema")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    execution: Mapped[PilotExecution] = relationship(back_populates="issues")

class PilotSourceComparison(Base):
    __tablename__ = "pilot_source_comparisons"
    __table_args__ = (UniqueConstraint("execution_id", "requirement_id", name="uq_pilot_source_comparison"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    execution_id: Mapped[int] = mapped_column(ForeignKey("pilot_executions.id"), index=True)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("pilot_source_requirements.id"), index=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("emission_sources.id"), nullable=True, index=True)
    platform_tco2e: Mapped[float] = mapped_column(Float, default=0)
    independent_tco2e: Mapped[float | None] = mapped_column(Float, nullable=True)
    absolute_difference_tco2e: Mapped[float | None] = mapped_column(Float, nullable=True)
    variance_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="Pendiente")
    notes: Mapped[str] = mapped_column(Text, default="")
    reviewed_by: Mapped[str] = mapped_column(String(180), default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    execution: Mapped[PilotExecution] = relationship(back_populates="comparisons")
    requirement: Mapped[PilotSourceRequirement] = relationship()
    source: Mapped[EmissionSource | None] = relationship()

class OperationalImportProfile(Base):
    __tablename__ = "operational_import_profiles"
    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_operational_import_profile_org_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    inventory_id: Mapped[int | None] = mapped_column(ForeignKey("inventories.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(180))
    source_format: Mapped[str] = mapped_column(String(20), default="XLSX")
    sheet_name: Mapped[str] = mapped_column(String(120), default="")
    delimiter: Mapped[str] = mapped_column(String(10), default=",")
    header_row: Mapped[int] = mapped_column(Integer, default=1)
    mapping_json: Mapped[str] = mapped_column(Text, default="{}")
    defaults_json: Mapped[str] = mapped_column(Text, default="{}")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(String(180), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship()
    inventory: Mapped[Inventory | None] = relationship()
    batches: Mapped[list["DataImportBatch"]] = relationship(back_populates="import_profile")

class DataImportBatch(Base):
    __tablename__ = "data_import_batches"
    __table_args__ = (UniqueConstraint("organization_id", "file_hash", name="uq_data_import_org_hash"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    execution_id: Mapped[int | None] = mapped_column(ForeignKey("pilot_executions.id"), nullable=True, index=True)
    inventory_id: Mapped[int | None] = mapped_column(ForeignKey("inventories.id"), nullable=True, index=True)
    import_profile_id: Mapped[int | None] = mapped_column(ForeignKey("operational_import_profiles.id"), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    filename: Mapped[str] = mapped_column(String(220))
    file_hash: Mapped[str] = mapped_column(String(64))
    source_format: Mapped[str] = mapped_column(String(20), default="XLSX")
    source_sheet: Mapped[str] = mapped_column(String(120), default="")
    mapping_json: Mapped[str] = mapped_column(Text, default="{}")
    original_headers_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(40), default="Cargado")
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, default=0)
    warning_rows: Mapped[int] = mapped_column(Integer, default=0)
    error_rows: Mapped[int] = mapped_column(Integer, default=0)
    applied_rows: Mapped[int] = mapped_column(Integer, default=0)
    quality_score: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_by: Mapped[str] = mapped_column(String(180), default="sistema")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    validated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")

    organization: Mapped[Organization] = relationship()
    execution: Mapped[PilotExecution | None] = relationship()
    inventory: Mapped[Inventory | None] = relationship()
    import_profile: Mapped[OperationalImportProfile | None] = relationship(back_populates="batches")
    rows: Mapped[list["DataImportRow"]] = relationship(back_populates="batch", cascade="all, delete-orphan")
    findings: Mapped[list["DataQualityFinding"]] = relationship(back_populates="batch", cascade="all, delete-orphan")

class DataImportRow(Base):
    __tablename__ = "data_import_rows"
    __table_args__ = (UniqueConstraint("batch_id", "row_number", name="uq_data_import_batch_row"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("data_import_batches.id"), index=True)
    row_number: Mapped[int] = mapped_column(Integer)
    requirement_code: Mapped[str] = mapped_column(String(80), default="")
    source_id: Mapped[int | None] = mapped_column(ForeignKey("emission_sources.id"), nullable=True, index=True)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(40), default="")
    evidence_reference: Mapped[str] = mapped_column(String(300), default="")
    data_origin: Mapped[str] = mapped_column(String(80), default="Registro operativo")
    is_estimated: Mapped[bool] = mapped_column(Boolean, default=False)
    quality_level: Mapped[str] = mapped_column(String(20), default="D")
    status: Mapped[str] = mapped_column(String(40), default="Pendiente")
    validation_messages: Mapped[str] = mapped_column(Text, default="[]")
    raw_payload_json: Mapped[str] = mapped_column(Text, default="{}")
    row_fingerprint: Mapped[str] = mapped_column(String(64), default="", index=True)
    duplicate_of_activity_id: Mapped[int | None] = mapped_column(ForeignKey("activity_data.id"), nullable=True, index=True)
    activity_data_id: Mapped[int | None] = mapped_column(ForeignKey("activity_data.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    batch: Mapped[DataImportBatch] = relationship(back_populates="rows")
    source: Mapped[EmissionSource | None] = relationship()
    duplicate_of_activity: Mapped[ActivityData | None] = relationship(foreign_keys=[duplicate_of_activity_id])
    activity_data: Mapped[ActivityData | None] = relationship(foreign_keys=[activity_data_id])
    findings: Mapped[list["DataQualityFinding"]] = relationship(back_populates="row", cascade="all, delete-orphan")

class DataQualityFinding(Base):
    __tablename__ = "data_quality_findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("data_import_batches.id"), index=True)
    row_id: Mapped[int | None] = mapped_column(ForeignKey("data_import_rows.id"), nullable=True, index=True)
    rule_code: Mapped[str] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(30), default="Advertencia")
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="Abierto")
    resolution: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    batch: Mapped[DataImportBatch] = relationship(back_populates="findings")
    row: Mapped[DataImportRow | None] = relationship(back_populates="findings")

class PeriodClose(Base):
    __tablename__ = "period_closes"
    __table_args__ = (UniqueConstraint("inventory_id", "period_start", "period_end", name="uq_period_close_inventory_period"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventories.id"), index=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40), default="Abierto")
    expected_sources: Mapped[int] = mapped_column(Integer, default=0)
    ready_sources: Mapped[int] = mapped_column(Integer, default=0)
    blocked_sources: Mapped[int] = mapped_column(Integer, default=0)
    data_coverage_percent: Mapped[int] = mapped_column(Integer, default=0)
    evidence_coverage_percent: Mapped[int] = mapped_column(Integer, default=0)
    quality_score: Mapped[int] = mapped_column(Integer, default=0)
    total_tco2e: Mapped[float] = mapped_column(Float, default=0)
    blockers_json: Mapped[str] = mapped_column(Text, default="[]")
    snapshot_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    snapshot_json: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    submitted_by: Mapped[str] = mapped_column(String(180), default="")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_by: Mapped[str] = mapped_column(String(180), default="")
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reopened_by: Mapped[str] = mapped_column(String(180), default="")
    reopened_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reopen_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship()
    inventory: Mapped[Inventory] = relationship()
    items: Mapped[list["PeriodCloseItem"]] = relationship(back_populates="period_close", cascade="all, delete-orphan")

class PeriodCloseItem(Base):
    __tablename__ = "period_close_items"
    __table_args__ = (UniqueConstraint("period_close_id", "source_id", name="uq_period_close_item_source"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    period_close_id: Mapped[int] = mapped_column(ForeignKey("period_closes.id"), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("emission_sources.id"), index=True)
    source_code: Mapped[str] = mapped_column(String(80), default="")
    source_name: Mapped[str] = mapped_column(String(220), default="")
    site: Mapped[str] = mapped_column(String(120), default="")
    scope: Mapped[int] = mapped_column(Integer, default=0)
    activity_records: Mapped[int] = mapped_column(Integer, default=0)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    estimated_records: Mapped[int] = mapped_column(Integer, default=0)
    quality_level: Mapped[str] = mapped_column(String(20), default="D")
    calculation_count: Mapped[int] = mapped_column(Integer, default=0)
    emissions_tco2e: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(40), default="Pendiente")
    snapshot_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    period_close: Mapped[PeriodClose] = relationship(back_populates="items")
    source: Mapped[EmissionSource] = relationship()
