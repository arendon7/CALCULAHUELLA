from __future__ import annotations

from collections import defaultdict
import math
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from .accounting import treatment_for
from .database import (
    ActivityData,
    EmissionCalculation,
    EmissionSource,
    EmissionFactorVersion,
    FactorDocumentation,
    GWPValue,
    Inventory,
    SourceFactorAssignment,
    UnitConversion,
    UnitDefinition,
)

ENGINE_VERSION = "0.45.0"


def assessment_from_inventory(inventory: Inventory) -> str:
    text = inventory.gwp_version.upper()
    for assessment in ("AR6", "AR5", "AR4"):
        if assessment in text:
            return assessment
    return "AR6"


def convert_value(session: Session, value: float, from_unit: str, to_unit: str) -> tuple[float | None, str]:
    if from_unit == to_unit:
        return value, "Sin conversión"
    direct = session.scalar(
        select(UnitConversion).where(
            UnitConversion.from_unit == from_unit,
            UnitConversion.to_unit == to_unit,
            UnitConversion.active.is_(True),
        )
    )
    if direct:
        converted = value * direct.multiplier + direct.offset
        return converted, f"{value:g} {from_unit} × {direct.multiplier:g} = {converted:g} {to_unit}"
    source_unit = session.scalar(select(UnitDefinition).where(UnitDefinition.code == from_unit, UnitDefinition.active.is_(True)))
    target_unit = session.scalar(select(UnitDefinition).where(UnitDefinition.code == to_unit, UnitDefinition.active.is_(True)))
    if not source_unit or not target_unit:
        return None, f"Unidad no registrada: {from_unit} o {to_unit}"
    if source_unit.dimension != target_unit.dimension:
        return None, f"Dimensiones incompatibles: {from_unit} ({source_unit.dimension}) → {to_unit} ({target_unit.dimension})"
    return None, f"No existe conversión configurada de {from_unit} a {to_unit}"


def _gwp_for_assignment(session: Session, assignment: SourceFactorAssignment, inventory: Inventory) -> float | None:
    gas_code = assignment.factor_version.gas.code
    if gas_code == "CO2e":
        return 1.0
    assessment = assessment_from_inventory(inventory)
    gwp = session.scalar(
        select(GWPValue).where(
            GWPValue.gas_id == assignment.factor_version.gas_id,
            GWPValue.assessment == assessment,
            GWPValue.horizon_years == 100,
            GWPValue.status == "Aprobado",
        )
    )
    return gwp.value if gwp else None


def calculate_record(session: Session, record: ActivityData) -> list[EmissionCalculation]:
    session.execute(delete(EmissionCalculation).where(EmissionCalculation.activity_data_id == record.id))
    source = session.scalar(
        select(EmissionSource)
        .where(EmissionSource.id == record.source_id)
        .options(
            selectinload(EmissionSource.inventory),
            selectinload(EmissionSource.factor_assignments)
            .selectinload(SourceFactorAssignment.factor_version)
            .selectinload(EmissionFactorVersion.gas),
        )
    )
    if not source:
        return []
    calculations: list[EmissionCalculation] = []
    assignments = [item for item in source.factor_assignments if item.active and item.factor_version.status == "Aprobado"]
    for assignment in assignments:
        factor = assignment.factor_version
        normalized, conversion_note = convert_value(session, record.value, record.unit, factor.input_unit)
        gas_code = factor.gas.code
        warning = ""
        status = "Calculado"
        gas_result = 0.0
        co2e = 0.0
        gwp = _gwp_for_assignment(session, assignment, source.inventory)
        if normalized is None:
            status = "Error"
            warning = conversion_note
            normalized_value = 0.0
            gwp_value = gwp or 0.0
        elif gwp is None:
            status = "Error"
            warning = f"No existe GWP aprobado para {gas_code} en {assessment_from_inventory(source.inventory)}."
            normalized_value = normalized
            gwp_value = 0.0
        else:
            normalized_value = normalized
            gwp_value = gwp
            gas_result = normalized * factor.value
            co2e = gas_result * gwp
            alerts: list[str] = []
            documentation = session.scalar(select(FactorDocumentation).where(FactorDocumentation.factor_version_id == factor.id))
            temporal_year = documentation.data_year if documentation and documentation.data_year is not None else factor.publication_year
            if temporal_year and temporal_year != record.period_start.year:
                alerts.append(f"El factor representa el año {temporal_year} y el dato corresponde a {record.period_start.year}. Validar representatividad temporal.")
            if documentation and documentation.reporting_use == "Demostrativo":
                alerts.append("Factor demostrativo: no apto para inventarios formales ni declaraciones verificadas.")
            if documentation and documentation.reporting_use == "Formal" and not documentation.review_status.startswith("Aprobado"):
                alerts.append(f"Documentación metodológica en estado {documentation.review_status}.")
            if alerts:
                warning = " ".join(alerts)
                status = "Con alerta"
        activity_uncertainty = max(float(getattr(record, "uncertainty_percentage", 0) or 0), 0.0)
        factor_uncertainty = max(float(factor.uncertainty_percentage or 0), 0.0)
        combined_uncertainty = math.sqrt(activity_uncertainty ** 2 + factor_uncertainty ** 2)
        lower_co2e = max(0.0, co2e * (1 - combined_uncertainty / 100))
        upper_co2e = co2e * (1 + combined_uncertainty / 100)
        reporting_bucket = treatment_for(source)
        formula = (
            f"{record.value:g} {record.unit} → {normalized_value:g} {factor.input_unit}; "
            f"{normalized_value:g} × {factor.value:g} {factor.output_unit}/{factor.input_unit} = {gas_result:g} kg {gas_code}; "
            f"× GWP {gwp_value:g} = {co2e:g} kg CO2e; "
            f"incertidumbre RSS √({activity_uncertainty:g}² + {factor_uncertainty:g}²) = {combined_uncertainty:g}%"
        )
        calculation = EmissionCalculation(
            activity_data_id=record.id,
            factor_version_id=factor.id,
            engine_version=ENGINE_VERSION,
            original_value=record.value,
            original_unit=record.unit,
            normalized_value=normalized_value,
            normalized_unit=factor.input_unit,
            factor_value=factor.value,
            gas_code=gas_code,
            gas_result_kg=gas_result,
            gwp_value=gwp_value,
            co2e_kg=co2e,
            reporting_bucket=reporting_bucket,
            uncertainty_percentage=combined_uncertainty,
            lower_co2e_kg=lower_co2e,
            upper_co2e_kg=upper_co2e,
            status=status,
            warning=warning,
            formula_snapshot=formula,
            calculated_at=datetime.now(UTC),
        )
        session.add(calculation)
        calculations.append(calculation)
    session.flush()
    return calculations


def recalculate_source(session: Session, source: EmissionSource) -> dict[str, object]:
    source = session.scalar(
        select(EmissionSource)
        .where(EmissionSource.id == source.id)
        .options(selectinload(EmissionSource.activity_records), selectinload(EmissionSource.inventory))
        .execution_options(populate_existing=True)
    )
    if not source:
        return {"calculations": 0, "warnings": ["Fuente no encontrada"], "emissions": 0.0}
    if source.category == "Datos específicos de proveedores":
        from .supply_chain import sync_supplier_source
        synced = sync_supplier_source(session, source.inventory_id)
        return {"calculations": 0, "warnings": [], "emissions": synced.emissions}
    warnings: list[str] = []
    calculation_count = 0
    for record in source.activity_records:
        results = calculate_record(session, record)
        calculation_count += len(results)
        warnings.extend(result.warning for result in results if result.warning)
    # Sum in Python to preserve portability across SQLite and PostgreSQL.
    rows = session.scalars(
        select(EmissionCalculation.co2e_kg).join(ActivityData).where(ActivityData.source_id == source.id)
    ).all()
    source.emissions = round(sum(rows) / 1000, 6)
    session.flush()
    return {"calculations": calculation_count, "warnings": warnings, "emissions": source.emissions}


def recalculate_inventory(session: Session, inventory: Inventory) -> dict[str, object]:
    inventory = session.scalar(
        select(Inventory)
        .where(Inventory.id == inventory.id)
        .options(selectinload(Inventory.sources))
        .execution_options(populate_existing=True)
    )
    if not inventory:
        return {"sources": 0, "calculations": 0, "warnings": []}
    total_calculations = 0
    warnings: list[str] = []
    for source in inventory.sources:
        result = recalculate_source(session, source)
        total_calculations += int(result["calculations"])
        warnings.extend(result["warnings"])
    session.flush()
    return {"sources": len(inventory.sources), "calculations": total_calculations, "warnings": warnings}


def source_calculation_summary(session: Session, source_id: int) -> dict[str, object]:
    calculations = session.scalars(
        select(EmissionCalculation)
        .join(ActivityData)
        .where(ActivityData.source_id == source_id)
        .options(selectinload(EmissionCalculation.factor_version).selectinload(EmissionFactorVersion.factor))
        .order_by(EmissionCalculation.calculated_at.desc())
    ).all()
    by_gas: dict[str, dict[str, float]] = defaultdict(lambda: {"gas_kg": 0.0, "co2e_kg": 0.0})
    warnings: list[str] = []
    for calculation in calculations:
        by_gas[calculation.gas_code]["gas_kg"] += calculation.gas_result_kg
        by_gas[calculation.gas_code]["co2e_kg"] += calculation.co2e_kg
        if calculation.warning and calculation.warning not in warnings:
            warnings.append(calculation.warning)
    return {
        "calculations": calculations,
        "by_gas": dict(by_gas),
        "warnings": warnings,
        "total_co2e_kg": sum(item.co2e_kg for item in calculations),
        "errors": sum(1 for item in calculations if item.status == "Error"),
        "alerts": sum(1 for item in calculations if item.status == "Con alerta"),
    }
