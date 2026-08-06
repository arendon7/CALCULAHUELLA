from __future__ import annotations

from collections import defaultdict
from typing import Iterable

PRODUCT_BOUNDARIES = ("De la cuna a la puerta", "De la cuna a la tumba", "Puerta a puerta", "Huella parcial")
LIFECYCLE_STAGES = (
    ("A1", "Materias primas"), ("A2", "Transporte de entrada"), ("A3", "Producción"),
    ("A4", "Empaque"), ("B1", "Distribución"), ("B2", "Uso"), ("C1", "Fin de vida"),
    ("BIO", "Biogénico y uso de la tierra"), ("OTR", "Otros procesos"),
)
ACCOUNTING_TYPES = ("Emisión", "Remoción", "Carbono almacenado", "Emisión evitada")
PROJECT_TYPES = ("Reducción de emisiones", "Aumento de remociones", "Eficiencia energética", "Energía renovable", "Residuos y circularidad", "Uso de la tierra", "Otro")
ASSURANCE_SUBJECTS = ("Inventario corporativo", "Huella de producto", "Proyecto de mitigación")
ASSURANCE_LEVELS = ("Limitado", "Razonable")


def normalize_co2e(value: float, output_unit: str) -> float:
    unit = (output_unit or "").strip().lower().replace("₂", "2").replace(" ", "")
    if value < 0:
        raise ValueError("El valor calculado no puede ser negativo; use el tipo contable para separar remociones.")
    if unit in {"gco2e", "gco2eq"}:
        return value / 1_000_000
    if unit in {"kgco2e", "kgco2eq"}:
        return value / 1_000
    if unit in {"tco2e", "tco2eq"}:
        return value
    raise ValueError("La unidad de salida debe ser g CO2e, kg CO2e o t CO2e.")


def calculate_product_stage(activity_value: float, factor_value: float, output_unit: str) -> float:
    if activity_value < 0 or factor_value < 0:
        raise ValueError("Actividad y factor deben ser mayores o iguales a cero.")
    return normalize_co2e(activity_value * factor_value, output_unit)


def product_summary(study) -> dict[str, object]:
    totals = defaultdict(float)
    warnings: list[str] = []
    stage_codes: set[str] = set()
    for item in study.stages:
        if item.excluded:
            if not item.exclusion_reason.strip():
                warnings.append(f"{item.stage_name}: la exclusión no tiene justificación.")
            continue
        stage_codes.add(item.stage_code)
        totals[item.accounting_type] += item.calculated_tco2e
        if not item.data_source.strip():
            warnings.append(f"{item.stage_name}: falta fuente del dato o factor.")
        if item.uncertainty_percentage > 30:
            warnings.append(f"{item.stage_name}: incertidumbre superior al 30 %.")
    gross = totals["Emisión"]
    removals = totals["Remoción"]
    net = gross - removals
    if study.boundary == "De la cuna a la puerta":
        required = {"A1", "A3"}
    elif study.boundary == "De la cuna a la tumba":
        required = {"A1", "A3", "B1", "B2", "C1"}
    else:
        required = set()
    missing = sorted(required - stage_codes)
    if missing:
        warnings.append("Etapas mínimas faltantes para el límite declarado: " + ", ".join(missing) + ".")
    if not study.pcr_reference.strip():
        warnings.append("No se documentó una PCR o regla sectorial aplicable; justificar su inexistencia o no aplicabilidad.")
    if study.reference_flow <= 0:
        warnings.append("El flujo de referencia debe ser mayor que cero.")
    blockers = [w for w in warnings if "mínimas faltantes" in w or "flujo de referencia" in w]
    return {
        "gross_emissions": gross,
        "removals": removals,
        "stored_carbon": totals["Carbono almacenado"],
        "avoided_emissions": totals["Emisión evitada"],
        "net_cfp": net,
        "per_declared_unit": net / study.reference_flow if study.reference_flow > 0 else 0,
        "warnings": warnings,
        "blockers": blockers,
        "stage_count": len(study.stages),
    }


def calculate_project_reduction(baseline: float, project: float, leakage: float, removals: float) -> float:
    if min(baseline, project, leakage, removals) < 0:
        raise ValueError("Las entradas del proyecto no pueden ser negativas.")
    return baseline - project - leakage + removals


def project_readiness(project) -> list[str]:
    issues: list[str] = []
    if project.end_date < project.start_date:
        issues.append("La fecha final es anterior a la inicial.")
    for label, value in (
        ("escenario de línea base", project.baseline_scenario),
        ("escenario del proyecto", project.project_scenario),
        ("adicionalidad", project.additionality_basis),
        ("plan de monitoreo", project.monitoring_plan),
        ("titularidad de resultados", project.ownership_statement),
        ("control de doble conteo", project.double_counting_control),
    ):
        if not str(value or "").strip():
            issues.append(f"Falta documentar {label}.")
    return issues


def project_summary(project) -> dict[str, object]:
    approved = [p for p in project.monitoring_periods if p.status == "Aprobado"]
    return {
        "estimated_reduction": project.estimated_reduction_tco2e,
        "monitored_reduction": sum(p.reduction_tco2e for p in approved),
        "period_count": len(project.monitoring_periods),
        "approved_periods": len(approved),
        "issues": project_readiness(project),
    }


def assurance_readiness(engagement) -> list[str]:
    issues: list[str] = []
    for label, value in (
        ("criterios", engagement.criteria), ("alcance", engagement.scope),
        ("declaración de independencia", engagement.independence_declaration),
        ("competencia del equipo", engagement.competence_basis),
        ("organismo verificador", engagement.verifier_organization),
        ("verificador líder", engagement.lead_verifier),
    ):
        if not str(value or "").strip():
            issues.append(f"Falta documentar {label}.")
    if engagement.end_date < engagement.start_date:
        issues.append("La fecha final es anterior a la inicial.")
    open_material = [f for f in engagement.findings if f.status != "Cerrado" and f.severity in {"Mayor", "Crítica"}]
    if open_material:
        issues.append(f"Existen {len(open_material)} hallazgos mayores o críticos abiertos.")
    return issues


def assurance_summary(engagements: Iterable) -> dict[str, object]:
    items = list(engagements)
    return {
        "count": len(items),
        "issued": sum(1 for e in items if e.status == "Declaración emitida"),
        "in_progress": sum(1 for e in items if e.status in {"Planificado", "En ejecución"}),
        "open_material_findings": sum(1 for e in items for f in e.findings if f.status != "Cerrado" and f.severity in {"Mayor", "Crítica"}),
    }
