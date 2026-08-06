from __future__ import annotations

from collections import defaultdict, deque
from datetime import UTC, datetime
import math
import re
import unicodedata

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from .accounting import treatment_for
from .factor_advisor import APPLIED_SELECTION_STATUSES
from .database import (
    ActivityData,
    ActivityFactorSelection,
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

ENGINE_VERSION = "1.1.0"
MAX_CONVERSION_HOPS = 4
APPROACH_1_GUIDANCE_THRESHOLD = 30.0

_UNIT_ALIASES = {
    "m3": "m³",
    "m^3": "m³",
    "metro cubico": "m³",
    "metros cubicos": "m³",
    "litro": "L",
    "litros": "L",
    "l": "L",
    "kwh": "kWh",
    "mwh": "MWh",
    "ton": "t",
    "tonelada": "t",
    "toneladas": "t",
}

_SUBSCRIPT_TRANSLATION = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")


def _finite_number(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def canonical_unit(unit: str) -> str:
    raw = (unit or "").strip()
    lookup = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii").lower()
    return _UNIT_ALIASES.get(lookup, raw)


def assessment_from_inventory(inventory: Inventory) -> str | None:
    text = (inventory.gwp_version or "").upper()
    for assessment in ("AR6", "AR5", "AR4"):
        if assessment in text:
            return assessment
    return None


def _conversion_graph(session: Session) -> dict[str, list[UnitConversion]]:
    graph: dict[str, list[UnitConversion]] = defaultdict(list)
    for item in session.scalars(select(UnitConversion).where(UnitConversion.active.is_(True))):
        graph[canonical_unit(item.from_unit)].append(item)
    return graph


def convert_value(session: Session, value: float, from_unit: str, to_unit: str) -> tuple[float | None, str]:
    numeric = _finite_number(value)
    if numeric is None:
        return None, "El dato de actividad no es un número finito."

    source_code = canonical_unit(from_unit)
    target_code = canonical_unit(to_unit)
    if not source_code or not target_code:
        return None, "La unidad de origen o destino está vacía."
    if source_code == target_code:
        return numeric, "Sin conversión"

    source_unit = session.scalar(
        select(UnitDefinition).where(UnitDefinition.code == source_code, UnitDefinition.active.is_(True))
    )
    target_unit = session.scalar(
        select(UnitDefinition).where(UnitDefinition.code == target_code, UnitDefinition.active.is_(True))
    )
    if not source_unit or not target_unit:
        return None, f"Unidad no registrada: {source_code} o {target_code}"
    if source_unit.dimension != target_unit.dimension:
        return None, (
            f"Dimensiones incompatibles: {source_code} ({source_unit.dimension}) → "
            f"{target_code} ({target_unit.dimension})"
        )

    direct = session.scalar(
        select(UnitConversion).where(
            UnitConversion.from_unit == source_code,
            UnitConversion.to_unit == target_code,
            UnitConversion.active.is_(True),
        )
    )
    if direct:
        converted = numeric * direct.multiplier + direct.offset
        if not math.isfinite(converted):
            return None, "La conversión produjo un resultado no finito."
        return converted, (
            f"{numeric:g} {source_code} × {direct.multiplier:g}"
            f"{' + ' + format(direct.offset, 'g') if direct.offset else ''} = {converted:g} {target_code}"
        )

    graph = _conversion_graph(session)
    # Cada estado conserva y = x·a + b. Esto permite encadenar también conversiones afines.
    queue: deque[tuple[str, float, float, list[str], int]] = deque(
        [(source_code, 1.0, 0.0, [source_code], 0)]
    )
    visited: set[str] = {source_code}
    while queue:
        current, multiplier, offset, path, hops = queue.popleft()
        if hops >= MAX_CONVERSION_HOPS:
            continue
        for edge in graph.get(current, []):
            next_code = canonical_unit(edge.to_unit)
            composed_multiplier = multiplier * edge.multiplier
            composed_offset = offset * edge.multiplier + edge.offset
            next_path = [*path, next_code]
            if next_code == target_code:
                converted = numeric * composed_multiplier + composed_offset
                if not math.isfinite(converted):
                    return None, "La conversión encadenada produjo un resultado no finito."
                path_text = " → ".join(next_path)
                return converted, (
                    f"Conversión encadenada {path_text}: {numeric:g} × {composed_multiplier:g}"
                    f"{' + ' + format(composed_offset, 'g') if composed_offset else ''} = {converted:g} {target_code}"
                )
            if next_code not in visited:
                visited.add(next_code)
                queue.append((next_code, composed_multiplier, composed_offset, next_path, hops + 1))

    return None, (
        f"No existe una ruta de conversión activa de {source_code} a {target_code} "
        f"dentro de {MAX_CONVERSION_HOPS} pasos."
    )


def _normalize_text(value: str) -> str:
    text = (value or "").translate(_SUBSCRIPT_TRANSLATION)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", text.strip().lower())


def normalize_factor_output(raw_result: float, output_unit: str, gas_code: str) -> tuple[float | None, str]:
    """Normaliza la salida de un factor a kg del gas declarado.

    El motor solo acepta salidas de masa explícitas (g, kg o t). De esta forma evita
    tratar silenciosamente toneladas o gramos como kilogramos.
    """
    numeric = _finite_number(raw_result)
    if numeric is None:
        return None, "El resultado bruto del factor no es un número finito."

    normalized = _normalize_text(output_unit).replace("co2 eq", "co2e").replace("co2-e", "co2e")
    compact = normalized.replace(" ", "")
    if compact.startswith("kg"):
        multiplier, mass_unit = 1.0, "kg"
        descriptor = compact[2:]
    elif compact.startswith("g"):
        multiplier, mass_unit = 0.001, "g"
        descriptor = compact[1:]
    elif compact.startswith("ton"):
        multiplier, mass_unit = 1000.0, "t"
        descriptor = compact[3:]
    elif compact.startswith("t"):
        multiplier, mass_unit = 1000.0, "t"
        descriptor = compact[1:]
    else:
        return None, (
            f"Unidad de salida no soportada: {output_unit}. Debe declarar masa en g, kg o t del gas."
        )

    expected = _normalize_text(gas_code).replace("-", "").replace(" ", "")
    descriptor = descriptor.replace("-", "").replace("_", "")
    generic_descriptor = descriptor in {"", "gas", "gei"}
    co2e_descriptor = descriptor in {"co2e", "co2eq", "co2equivalente", "co2equivalentes"}
    gas_matches = expected in descriptor or descriptor in expected

    if expected == "co2e":
        if not (generic_descriptor or co2e_descriptor):
            return None, f"La salida {output_unit} no corresponde al gas agregado CO2e."
    elif not (generic_descriptor or gas_matches):
        return None, f"La salida {output_unit} no corresponde al gas declarado {gas_code}."

    result_kg = numeric * multiplier
    if not math.isfinite(result_kg):
        return None, "La normalización de la salida produjo un resultado no finito."
    if mass_unit == "kg":
        return result_kg, f"{numeric:g} {output_unit} = {result_kg:g} kg {gas_code}"
    return result_kg, f"{numeric:g} {output_unit} × {multiplier:g} = {result_kg:g} kg {gas_code}"


def combine_relative_uncertainty(
    activity_uncertainty: float,
    factor_uncertainty: float,
) -> tuple[float | None, list[str]]:
    activity = _finite_number(activity_uncertainty)
    factor = _finite_number(factor_uncertainty)
    if activity is None or factor is None:
        return None, ["La incertidumbre del dato o del factor no es un número finito."]
    if activity < 0 or factor < 0:
        return None, ["La incertidumbre del dato y del factor debe ser mayor o igual a cero."]
    alerts: list[str] = []
    if max(activity, factor) > APPROACH_1_GUIDANCE_THRESHOLD:
        alerts.append(
            "Alguna incertidumbre de entrada supera 30 %. El rango RSS (Approach 1) es orientativo; "
            "evaluar distribución, correlaciones y Approach 2/Monte Carlo."
        )
    return math.sqrt(activity ** 2 + factor ** 2), alerts


def _gwp_for_assignment(session: Session, assignment: SourceFactorAssignment, inventory: Inventory) -> float | None:
    gas_code = assignment.factor_version.gas.code
    if gas_code == "CO2e":
        return 1.0
    assessment = assessment_from_inventory(inventory)
    if assessment is None:
        return None
    gwp = session.scalar(
        select(GWPValue).where(
            GWPValue.gas_id == assignment.factor_version.gas_id,
            GWPValue.assessment == assessment,
            GWPValue.horizon_years == 100,
            GWPValue.status == "Aprobado",
        )
    )
    return gwp.value if gwp else None


def _factor_validity_alerts(factor: EmissionFactorVersion, record: ActivityData) -> list[str]:
    alerts: list[str] = []
    if factor.effective_from and record.period_end < factor.effective_from:
        alerts.append(
            f"El factor entra en vigencia el {factor.effective_from.isoformat()} y el dato termina el "
            f"{record.period_end.isoformat()}."
        )
    if factor.effective_to and record.period_start > factor.effective_to:
        alerts.append(
            f"El factor dejó de estar vigente el {factor.effective_to.isoformat()} y el dato inicia el "
            f"{record.period_start.isoformat()}."
        )
    return alerts


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
    specific = list(
        session.scalars(
            select(ActivityFactorSelection)
            .where(
                ActivityFactorSelection.activity_data_id == record.id,
                ActivityFactorSelection.active.is_(True),
                ActivityFactorSelection.selection_status.in_(APPLIED_SELECTION_STATUSES),
            )
            .options(selectinload(ActivityFactorSelection.factor_version).selectinload(EmissionFactorVersion.gas))
        )
    )
    assignments = specific or [
        item for item in source.factor_assignments if item.active and item.factor_version.status == "Aprobado"
    ]
    approved_assignments = [item for item in assignments if item.factor_version.status == "Aprobado"]
    gas_codes = {item.factor_version.gas.code for item in approved_assignments}
    mixed_aggregation = "CO2e" in gas_codes and any(code != "CO2e" for code in gas_codes)
    assessment = assessment_from_inventory(source.inventory)

    for assignment in approved_assignments:
        factor = assignment.factor_version
        gas_code = factor.gas.code
        normalized_value = 0.0
        gas_result = 0.0
        co2e = 0.0
        gwp_value = 0.0
        warning_parts: list[str] = []
        status = "Calculado"
        conversion_note = "Conversión no ejecutada"
        output_note = "Normalización de salida no ejecutada"

        record_value = _finite_number(record.value)
        factor_value = _finite_number(factor.value)
        if record_value is None or record_value < 0:
            status = "Error"
            warning_parts.append("El dato de actividad debe ser un número finito mayor o igual a cero.")
        if factor_value is None or factor_value < 0:
            status = "Error"
            warning_parts.append("El valor del factor debe ser un número finito mayor o igual a cero.")
        if mixed_aggregation:
            status = "Error"
            warning_parts.append(
                "No se permite mezclar un factor agregado en CO2e con factores desagregados por gas para el mismo dato; "
                "la combinación puede duplicar emisiones."
            )
        if assessment is None and gas_code != "CO2e":
            status = "Error"
            warning_parts.append(
                f"La configuración GWP ‘{source.inventory.gwp_version}’ es ambigua. Debe identificar AR4, AR5 o AR6."
            )

        normalized, conversion_note = convert_value(
            session,
            record_value if record_value is not None else float("nan"),
            record.unit,
            factor.input_unit,
        )
        if normalized is None:
            status = "Error"
            warning_parts.append(conversion_note)
        else:
            normalized_value = normalized

        gwp = _gwp_for_assignment(session, assignment, source.inventory)
        if gwp is None:
            status = "Error"
            warning_parts.append(
                f"No existe GWP100 aprobado para {gas_code} en {assessment or 'la evaluación configurada'}."
            )
        else:
            gwp_value = gwp

        if status != "Error" and factor_value is not None:
            raw_factor_result = normalized_value * factor_value
            normalized_output, output_note = normalize_factor_output(raw_factor_result, factor.output_unit, gas_code)
            if normalized_output is None:
                status = "Error"
                warning_parts.append(output_note)
            else:
                gas_result = normalized_output
                co2e = gas_result * gwp_value
                if not math.isfinite(co2e):
                    status = "Error"
                    gas_result = 0.0
                    co2e = 0.0
                    warning_parts.append("El cálculo produjo un resultado de emisiones no finito.")

        documentation = session.scalar(
            select(FactorDocumentation).where(FactorDocumentation.factor_version_id == factor.id)
        )
        if status != "Error":
            temporal_year = (
                documentation.data_year
                if documentation and documentation.data_year is not None
                else factor.publication_year
            )
            if temporal_year and temporal_year != record.period_start.year:
                warning_parts.append(
                    f"El factor representa el año {temporal_year} y el dato corresponde a "
                    f"{record.period_start.year}. Validar representatividad temporal."
                )
            warning_parts.extend(_factor_validity_alerts(factor, record))
            if documentation and documentation.reporting_use == "Demostrativo":
                warning_parts.append(
                    "Factor demostrativo: no apto para inventarios formales ni declaraciones verificadas."
                )
            if (
                documentation
                and documentation.reporting_use == "Formal"
                and not documentation.review_status.startswith("Aprobado")
            ):
                warning_parts.append(f"Documentación metodológica en estado {documentation.review_status}.")
            if gas_code in {"CH4", "CH4-FOSSIL"} and (
                not documentation
                or documentation.methane_origin in {"", "No aplica", "No documentado"}
            ):
                warning_parts.append(
                    "El origen del metano no está documentado; confirmar si corresponde a metano fósil o no fósil."
                )
            if gas_code == "CO2e" and documentation and documentation.aggregated_co2e and not documentation.gwp_embedded:
                warning_parts.append(
                    "El factor agregado no identifica la evaluación GWP incorporada; documentarla antes de uso formal."
                )

        activity_uncertainty = getattr(record, "uncertainty_percentage", 0) or 0
        factor_uncertainty = factor.uncertainty_percentage or 0
        activity_uncertainty_number = _finite_number(activity_uncertainty)
        factor_uncertainty_number = _finite_number(factor_uncertainty)
        combined_uncertainty, uncertainty_alerts = combine_relative_uncertainty(
            activity_uncertainty,
            factor_uncertainty,
        )
        if combined_uncertainty is None:
            status = "Error"
            combined_uncertainty = 0.0
            warning_parts.extend(uncertainty_alerts)
        else:
            warning_parts.extend(uncertainty_alerts)

        if status != "Error" and warning_parts:
            status = "Con alerta"
        lower_co2e = max(0.0, co2e * (1 - combined_uncertainty / 100))
        upper_co2e = co2e * (1 + combined_uncertainty / 100)
        reporting_bucket = treatment_for(source)
        raw_result = normalized_value * (factor_value or 0.0)
        formula = (
            f"Motor {ENGINE_VERSION}; {record.value:g} {record.unit} → {normalized_value:g} {factor.input_unit} "
            f"({conversion_note}); {normalized_value:g} × {(factor_value or 0):g} "
            f"{factor.output_unit}/{factor.input_unit} = {raw_result:g} {factor.output_unit}; "
            f"{output_note}; × GWP100 {gwp_value:g} ({assessment or 'incorporado/no aplicable'}) = "
            f"{co2e:g} kg CO2e; incertidumbre RSS √({(activity_uncertainty_number or 0):g}² + "
            f"{(factor_uncertainty_number or 0):g}²) = {combined_uncertainty:g}% (rango orientativo)."
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
            warning=" ".join(dict.fromkeys(part for part in warning_parts if part)),
            formula_snapshot=formula,
            calculated_at=datetime.now(UTC),
        )
        session.add(calculation)
        calculations.append(calculation)
    session.flush()
    return calculations


def recalculate_source(session: Session, source: EmissionSource) -> dict[str, object]:
    # Garantiza que cambios metodológicos pendientes en la misma transacción sean visibles al recalcular.
    session.flush()
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
        select(EmissionCalculation.co2e_kg)
        .join(ActivityData)
        .where(ActivityData.source_id == source.id, EmissionCalculation.status != "Error")
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
    valid_calculations = [item for item in calculations if item.status != "Error"]
    for calculation in valid_calculations:
        by_gas[calculation.gas_code]["gas_kg"] += calculation.gas_result_kg
        by_gas[calculation.gas_code]["co2e_kg"] += calculation.co2e_kg
    for calculation in calculations:
        if calculation.warning and calculation.warning not in warnings:
            warnings.append(calculation.warning)
    return {
        "calculations": calculations,
        "by_gas": dict(by_gas),
        "warnings": warnings,
        "total_co2e_kg": sum(item.co2e_kg for item in valid_calculations),
        "errors": sum(1 for item in calculations if item.status == "Error"),
        "alerts": sum(1 for item in calculations if item.status == "Con alerta"),
    }
