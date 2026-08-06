from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base

class ConsolidationFinding(Base):
    __tablename__ = "consolidation_findings"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_consolidation_finding_org_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    code: Mapped[str] = mapped_column(String(40))
    area: Mapped[str] = mapped_column(String(80), default="Producto")
    title: Mapped[str] = mapped_column(String(220))
    detail: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(30), default="Media")
    status: Mapped[str] = mapped_column(String(40), default="Abierto")
    owner: Mapped[str] = mapped_column(String(180), default="Equipo de producto")
    target_version: Mapped[str] = mapped_column(String(30), default="V1.0")
    evidence: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(180), default="sistema")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship()

class ReleaseGate(Base):
    __tablename__ = "release_gates"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_release_gate_org_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    code: Mapped[str] = mapped_column(String(40))
    category: Mapped[str] = mapped_column(String(80), default="Producto")
    name: Mapped[str] = mapped_column(String(220))
    status: Mapped[str] = mapped_column(String(40), default="Pendiente")
    responsible: Mapped[str] = mapped_column(String(180), default="Equipo de producto")
    evidence: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship()

class JourneyValidation(Base):
    __tablename__ = "journey_validations"
    __table_args__ = (UniqueConstraint("organization_id", "journey_code", name="uq_journey_validation_org_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    journey_code: Mapped[str] = mapped_column(String(60))
    role: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40), default="No probado")
    tested_by: Mapped[str] = mapped_column(String(180), default="")
    tested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    organization: Mapped[Organization] = relationship()

class MethodologySourceDocument(Base):
    __tablename__ = "methodology_source_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(260))
    issuing_body: Mapped[str] = mapped_column(String(180))
    document_type: Mapped[str] = mapped_column(String(100), default="Guía metodológica")
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    jurisdiction: Mapped[str] = mapped_column(String(120), default="Internacional")
    source_url: Mapped[str] = mapped_column(String(500), default="")
    citation: Mapped[str] = mapped_column(Text, default="")
    checksum_sha256: Mapped[str] = mapped_column(String(64), default="")
    # Los estados documentales incluyen calificaciones completas de vigencia,
    # parametrización y revisión; 40 caracteres truncaba valores válidos.
    status: Mapped[str] = mapped_column(String(160), default="Vigente")
    accessed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    factor_documentation: Mapped[list["FactorDocumentation"]] = relationship(back_populates="source_document")

class FactorDocumentation(Base):
    __tablename__ = "factor_documentation"
    __table_args__ = (UniqueConstraint("factor_version_id", name="uq_factor_documentation_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    factor_version_id: Mapped[int] = mapped_column(ForeignKey("emission_factor_versions.id"), index=True)
    source_document_id: Mapped[int | None] = mapped_column(ForeignKey("methodology_source_documents.id"), nullable=True)
    factor_kind: Mapped[str] = mapped_column(String(80), default="Demostrativo")
    reporting_use: Mapped[str] = mapped_column(String(40), default="Demostrativo")
    page_reference: Mapped[str] = mapped_column(String(80), default="")
    table_reference: Mapped[str] = mapped_column(String(120), default="")
    data_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_unit: Mapped[str] = mapped_column(String(100), default="")
    conversion_expression: Mapped[str] = mapped_column(Text, default="")
    aggregated_co2e: Mapped[bool] = mapped_column(Boolean, default=False)
    gwp_embedded: Mapped[str] = mapped_column(String(80), default="")
    methane_origin: Mapped[str] = mapped_column(String(40), default="No aplica")
    quality_grade: Mapped[str] = mapped_column(String(10), default="D")
    review_status: Mapped[str] = mapped_column(String(40), default="Pendiente")
    reviewer: Mapped[str] = mapped_column(String(180), default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    restriction_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    factor_version: Mapped[EmissionFactorVersion] = relationship()
    source_document: Mapped[MethodologySourceDocument | None] = relationship(back_populates="factor_documentation")

class FactorSelectionRule(Base):
    __tablename__ = "factor_selection_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    name: Mapped[str] = mapped_column(String(220))
    activity_type: Mapped[str] = mapped_column(String(120), default="*")
    country: Mapped[str] = mapped_column(String(100), default="*")
    input_unit: Mapped[str] = mapped_column(String(40), default="*")
    gas_code: Mapped[str] = mapped_column(String(40), default="*")
    preferred_factor_kind: Mapped[str] = mapped_column(String(80), default="Oficial nacional")
    requires_year_match: Mapped[bool] = mapped_column(Boolean, default=True)
    max_year_gap: Mapped[int] = mapped_column(Integer, default=1)
    minimum_quality_grade: Mapped[str] = mapped_column(String(10), default="B")
    allowed_reporting_use: Mapped[str] = mapped_column(String(40), default="Formal")
    status: Mapped[str] = mapped_column(String(30), default="Activa")
    rationale: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

class ReferenceCalculationCase(Base):
    __tablename__ = "reference_calculation_cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(220))
    category: Mapped[str] = mapped_column(String(100), default="Motor")
    description: Mapped[str] = mapped_column(Text, default="")
    activity_value: Mapped[float] = mapped_column(Float)
    activity_unit: Mapped[str] = mapped_column(String(40))
    factor_value: Mapped[float] = mapped_column(Float)
    factor_input_unit: Mapped[str] = mapped_column(String(40))
    gas_code: Mapped[str] = mapped_column(String(40))
    gwp_value: Mapped[float] = mapped_column(Float, default=1)
    expected_normalized_value: Mapped[float] = mapped_column(Float)
    expected_gas_kg: Mapped[float] = mapped_column(Float)
    expected_co2e_kg: Mapped[float] = mapped_column(Float)
    tolerance: Mapped[float] = mapped_column(Float, default=0.000001)
    expected_status: Mapped[str] = mapped_column(String(40), default="Calculado")
    source_reference: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    results: Mapped[list["ReferenceCaseResult"]] = relationship(back_populates="case", cascade="all, delete-orphan")

class MethodologyValidationRun(Base):
    __tablename__ = "methodology_validation_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    engine_version: Mapped[str] = mapped_column(String(30))
    executed_by: Mapped[str] = mapped_column(String(180), default="sistema")
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    total_cases: Mapped[int] = mapped_column(Integer, default=0)
    passed_cases: Mapped[int] = mapped_column(Integer, default=0)
    failed_cases: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="Pendiente")
    details_json: Mapped[str] = mapped_column(Text, default="{}")

    results: Mapped[list["ReferenceCaseResult"]] = relationship(back_populates="run", cascade="all, delete-orphan")

class ReferenceCaseResult(Base):
    __tablename__ = "reference_case_results"
    __table_args__ = (UniqueConstraint("run_id", "case_id", name="uq_reference_case_result"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("methodology_validation_runs.id"), index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("reference_calculation_cases.id"), index=True)
    normalized_value: Mapped[float] = mapped_column(Float, default=0)
    gas_kg: Mapped[float] = mapped_column(Float, default=0)
    co2e_kg: Mapped[float] = mapped_column(Float, default=0)
    absolute_difference: Mapped[float] = mapped_column(Float, default=0)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(40), default="Pendiente")
    detail: Mapped[str] = mapped_column(Text, default="")

    run: Mapped[MethodologyValidationRun] = relationship(back_populates="results")
    case: Mapped[ReferenceCalculationCase] = relationship(back_populates="results")
