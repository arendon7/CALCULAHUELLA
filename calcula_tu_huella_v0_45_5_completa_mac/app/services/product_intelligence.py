from __future__ import annotations

import json
import math
import secrets
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import (
    CommercialLead,
    DiagnosticAssessment,
    ImplementationPlan,
    ImplementationPlanItem,
    Organization,
    OrganizationCarbonProfile,
    add_audit,
)
from ..repositories.product_intelligence import get_or_create_carbon_profile

PACKAGE_LABELS: dict[str, str] = {
    "ESENCIAL": "Huella Esencial",
    "EMPRESARIAL": "Gestión de Carbono",
    "CORPORATIVO": "Gestión Avanzada y Verificación",
}

PACKAGE_DESCRIPTIONS: dict[str, str] = {
    "ESENCIAL": "Diagnóstico, alcances 1 y 2, carga anual, cálculo asistido e informe ejecutivo.",
    "EMPRESARIAL": "Gestión periódica, alcance 3 priorizado, calidad, cierre, indicadores y plan de reducción.",
    "CORPORATIVO": "Alcance 3 profundo, proveedores, verificación, incertidumbre, escenarios, riesgos y memoria técnica.",
}


def _json_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        try:
            decoded = json.loads(stripped)
            if isinstance(decoded, list):
                return [str(item).strip() for item in decoded if str(item).strip()]
        except json.JSONDecodeError:
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return [stripped]
    if isinstance(value, Iterable):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def _dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "si", "sí", "on", "x"}


def _requests_verification(value: str) -> bool:
    normalized = (value or "").strip().casefold()
    if not normalized or normalized.startswith(("sin ", "no ")):
        return False
    return "verific" in normalized or "asegur" in normalized


def _band_score(value: str, mapping: dict[str, int], default: int = 0) -> int:
    normalized = value.strip().casefold()
    for key, score in mapping.items():
        if key.casefold() in normalized:
            return score
    return default


@dataclass(frozen=True)
class AssessmentResult:
    company_size_score: int
    operational_complexity_score: int
    scope_complexity_score: int
    data_maturity_score: int
    governance_maturity_score: int
    reporting_pressure_score: int
    verification_readiness_score: int
    total_score: int
    maturity_level: str
    complexity_level: str
    package_code: str
    duration_months: int
    effort_hours: int
    recommended_scopes: list[str]
    applicable_modules: list[str]
    probable_sources: list[str]
    priority_scope3_categories: list[str]
    exclusions: list[str]
    findings: list[str]
    risk_flags: list[str]
    next_steps: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "company_size_score": self.company_size_score,
            "operational_complexity_score": self.operational_complexity_score,
            "scope_complexity_score": self.scope_complexity_score,
            "data_maturity_score": self.data_maturity_score,
            "governance_maturity_score": self.governance_maturity_score,
            "reporting_pressure_score": self.reporting_pressure_score,
            "verification_readiness_score": self.verification_readiness_score,
            "total_score": self.total_score,
            "maturity_level": self.maturity_level,
            "complexity_level": self.complexity_level,
            "package_code": self.package_code,
            "package_label": PACKAGE_LABELS[self.package_code],
            "package_description": PACKAGE_DESCRIPTIONS[self.package_code],
            "duration_months": self.duration_months,
            "effort_hours": self.effort_hours,
            "recommended_scopes": self.recommended_scopes,
            "applicable_modules": self.applicable_modules,
            "probable_sources": self.probable_sources,
            "priority_scope3_categories": self.priority_scope3_categories,
            "exclusions": self.exclusions,
            "findings": self.findings,
            "risk_flags": self.risk_flags,
            "next_steps": self.next_steps,
        }


def assess_company(payload: dict[str, Any]) -> AssessmentResult:
    """Generate an explainable recommendation from the organization's context.

    This engine does not certify an inventory or select an emission factor. It
    determines the depth of work, probable sources and modules that require
    human confirmation before implementation.
    """
    employees_band = str(payload.get("employees_band") or payload.get("company_size") or "")
    employees = int(payload.get("employees") or 0)
    if employees_band:
        size_score = _band_score(employees_band, {"1 a 20": 1, "21 a 50": 2, "51 a 200": 4, "más de 200": 6}, 2)
    else:
        size_score = 1 if employees <= 20 else 2 if employees <= 50 else 4 if employees <= 200 else 6

    facilities = max(1, int(payload.get("facilities_count") or 1))
    countries = max(1, int(payload.get("countries_count") or 1))
    flags = {
        "fleet": _truthy(payload.get("has_fleet")),
        "fuels": _truthy(payload.get("uses_fuels")),
        "refrigerants": _truthy(payload.get("uses_refrigerants")),
        "waste": _truthy(payload.get("manages_waste")),
        "wastewater": _truthy(payload.get("has_wastewater")),
        "agriculture": _truthy(payload.get("has_agriculture")),
        "suppliers": _truthy(payload.get("relies_on_suppliers")),
        "generation": _truthy(payload.get("owns_generation")),
        "process": _truthy(payload.get("has_process_emissions")),
    }
    core_processes = _json_list(payload.get("core_processes"))
    sector = str(payload.get("sector") or "").casefold()

    operational = min(facilities, 8) + min(max(countries - 1, 0) * 2, 6)
    operational += sum(2 if key in {"process", "agriculture", "wastewater"} and active else 1 if active else 0 for key, active in flags.items())
    operational += min(len(core_processes), 5)
    if any(term in sector for term in ("manufact", "residu", "agro", "min", "cement", "quím", "transport")):
        operational += 2

    desired_scopes = str(payload.get("desired_scopes") or "Alcances 1 y 2")
    scope_complexity = 2
    if "3" in desired_scopes:
        scope_complexity += 5
    if "avanz" in desired_scopes.casefold():
        scope_complexity += 4
    if flags["suppliers"]:
        scope_complexity += 3
    if countries > 1:
        scope_complexity += 2

    data_availability = str(payload.get("data_availability") or "Baja")
    evidence_readiness = str(payload.get("evidence_readiness") or "Baja")
    data_score = _band_score(data_availability, {"baja": 20, "parcial": 45, "media": 60, "alta": 80, "completa": 95}, 35)
    evidence_score = _band_score(evidence_readiness, {"baja": 15, "parcial": 40, "media": 60, "alta": 82, "completa": 95}, 30)
    history_bonus = 12 if _truthy(payload.get("has_previous_inventory")) or "anterior" in str(payload.get("inventory_history") or "").casefold() else 0
    systems = _json_list(payload.get("current_data_systems"))
    data_maturity = min(100, round(data_score * 0.55 + evidence_score * 0.35 + history_bonus + min(len(systems) * 3, 9)))

    owner = str(payload.get("inventory_owner") or "").strip()
    sponsor = str(payload.get("executive_sponsor") or "").strip()
    reporting_frequency = str(payload.get("reporting_frequency") or "Anual")
    governance = 20 + (25 if owner else 0) + (20 if sponsor else 0)
    governance += 20 if reporting_frequency == "Mensual" else 12 if reporting_frequency == "Trimestral" else 5
    governance += 10 if _truthy(payload.get("has_previous_inventory")) else 0
    governance = min(governance, 100)

    objective = str(payload.get("objective") or "Conocer la huella corporativa")
    objective_lower = objective.casefold()
    assurance = str(payload.get("assurance_ambition") or "Sin verificación externa")
    assurance_lower = assurance.casefold()
    urgency = str(payload.get("urgency") or "Normal")
    deadline_months = max(1, int(payload.get("deadline_months") or 12))
    reporting_pressure = 15
    if any(term in objective_lower for term in ("regulator", "licit", "cliente", "sostenibilidad", "financ")):
        reporting_pressure += 35
    verification_requested = _requests_verification(objective) or _requests_verification(assurance)
    if verification_requested:
        reporting_pressure += 30
    if urgency == "Alta" or deadline_months <= 4:
        reporting_pressure += 20
    reporting_pressure = min(reporting_pressure, 100)

    verification_readiness = round(data_maturity * 0.45 + governance * 0.35 + (20 if _truthy(payload.get("has_previous_inventory")) else 5))
    verification_readiness = min(100, verification_readiness)

    complexity_total = size_score + operational + scope_complexity + round(reporting_pressure / 20)
    complexity_level = "Baja" if complexity_total <= 12 else "Media" if complexity_total <= 22 else "Alta" if complexity_total <= 32 else "Muy alta"
    maturity_average = round((data_maturity + governance + verification_readiness) / 3)
    maturity_level = "Inicial" if maturity_average < 35 else "En desarrollo" if maturity_average < 60 else "Gestionada" if maturity_average < 80 else "Avanzada"

    strict_driver = any((
        _requests_verification(objective),
        "regulator" in objective_lower,
        _requests_verification(assurance),
        countries > 1,
        "avanz" in desired_scopes.casefold(),
    ))
    if strict_driver or complexity_total >= 29:
        package = "CORPORATIVO"
    elif complexity_total >= 14 or "3" in desired_scopes or reporting_frequency in {"Mensual", "Trimestral"}:
        package = "EMPRESARIAL"
    else:
        package = "ESENCIAL"

    recommended_scopes = ["Alcance 1", "Alcance 2"]
    if "3" in desired_scopes or flags["suppliers"] or flags["waste"]:
        recommended_scopes.append("Alcance 3 priorizado" if package != "CORPORATIVO" else "Alcance 3 avanzado")

    probable_sources: list[str] = ["Electricidad adquirida"]
    if flags["fuels"] or flags["generation"]:
        probable_sources.append("Combustión fija y generación propia")
    if flags["fleet"]:
        probable_sources.append("Combustión móvil de flota propia")
    if flags["refrigerants"]:
        probable_sources.append("Fugas y recargas de refrigerantes")
    if flags["process"]:
        probable_sources.append("Emisiones de proceso")
    if flags["wastewater"]:
        probable_sources.append("Tratamiento de aguas residuales")
    if flags["waste"]:
        probable_sources.append("Tratamiento, aprovechamiento y disposición de residuos")
    if flags["agriculture"]:
        probable_sources.extend(["Fertilización y manejo de suelos", "Uso de suelo y emisiones biogénicas"])
    if flags["suppliers"]:
        probable_sources.extend(["Bienes y servicios adquiridos", "Transporte contratado y cadena de valor"])
    if "manufact" in sector:
        probable_sources.append("Materias primas y procesos manufactureros")
    probable_sources = list(dict.fromkeys(probable_sources))

    priority_scope3: list[str] = []
    if flags["suppliers"]:
        priority_scope3.append("Categoría 1 · Bienes y servicios adquiridos")
    if flags["waste"]:
        priority_scope3.append("Categoría 5 · Residuos generados en las operaciones")
    if flags["fleet"] or flags["suppliers"]:
        priority_scope3.append("Categorías 4 y 9 · Transporte y distribución")
    if employees > 20 or size_score >= 2:
        priority_scope3.extend(["Categoría 6 · Viajes de negocio", "Categoría 7 · Desplazamiento de empleados"])
    priority_scope3 = list(dict.fromkeys(priority_scope3))

    modules = ["Perfil y diagnóstico", "Inventarios y límites", "Datos y evidencias", "Motor de cálculo", "Informes"]
    if package in {"EMPRESARIAL", "CORPORATIVO"}:
        modules.extend(["Cargas operativas", "Calidad de datos", "Cierre mensual", "Plan de reducción", "Indicadores"])
    if "3" in desired_scopes or flags["suppliers"]:
        modules.append("Cadena de valor y proveedores")
    if package == "CORPORATIVO":
        modules.extend(["Portal del verificador", "Incertidumbre y año base", "Escenarios y MACC", "Riesgos y divulgación climática"])
    modules = list(dict.fromkeys(modules))

    findings: list[str] = []
    risks: list[str] = []
    if data_maturity < 50:
        findings.append("La prioridad inicial es organizar propietarios, formatos y soportes antes de ampliar el alcance.")
        risks.append("Disponibilidad o trazabilidad de datos insuficiente")
    if governance < 55:
        findings.append("Debe formalizarse un responsable del inventario y un patrocinador directivo.")
        risks.append("Gobierno climático dependiente de personas y no de un proceso")
    if flags["suppliers"]:
        findings.append("El alcance 3 requiere segmentar proveedores por gasto, relevancia y calidad de información.")
    if verification_requested:
        findings.append("La preparación para verificación exige evidencia reproducible, independencia y control de cambios.")
        if verification_readiness < 70:
            risks.append("La organización aún no está lista para aseguramiento externo")
    if countries > 1:
        findings.append("Se requiere una política común de consolidación y factores por jurisdicción.")
    if not findings:
        findings.append("La organización puede iniciar con un inventario acotado y ampliar categorías en el siguiente periodo.")

    exclusions: list[str] = []
    if package == "ESENCIAL":
        exclusions.extend(["Alcance 3 exhaustivo", "Verificación externa", "Modelación climática avanzada"])
    elif package == "EMPRESARIAL":
        exclusions.extend(["Categorías de alcance 3 no materiales", "Verificación externa salvo contratación adicional"])
    else:
        exclusions.append("Ninguna exclusión automática: aplicar materialidad y documentar toda exclusión")

    next_steps = [
        "Validar el perfil operativo y los límites organizacionales con la dirección.",
        "Confirmar fuentes probables, responsables, periodicidad y evidencia disponible.",
        "Aprobar el paquete y la profundidad metodológica antes de cargar información.",
        "Ejecutar el plan por fases y registrar cambios de alcance o metodología.",
    ]
    if data_maturity < 50:
        next_steps.insert(1, "Crear un plan de datos con formatos, responsables y controles mínimos.")
    if package == "CORPORATIVO":
        next_steps.append("Programar revisión metodológica independiente y preparación para verificación.")

    duration = 2 if package == "ESENCIAL" else 4 if package == "EMPRESARIAL" else 6
    duration += 1 if countries > 1 else 0
    effort = 40 if package == "ESENCIAL" else 110 if package == "EMPRESARIAL" else 220
    effort += facilities * (4 if package == "ESENCIAL" else 8)
    effort += len(priority_scope3) * 8

    return AssessmentResult(
        company_size_score=size_score,
        operational_complexity_score=operational,
        scope_complexity_score=scope_complexity,
        data_maturity_score=data_maturity,
        governance_maturity_score=governance,
        reporting_pressure_score=reporting_pressure,
        verification_readiness_score=verification_readiness,
        total_score=complexity_total,
        maturity_level=maturity_level,
        complexity_level=complexity_level,
        package_code=package,
        duration_months=duration,
        effort_hours=effort,
        recommended_scopes=recommended_scopes,
        applicable_modules=modules,
        probable_sources=probable_sources,
        priority_scope3_categories=priority_scope3,
        exclusions=exclusions,
        findings=findings,
        risk_flags=risks,
        next_steps=next_steps,
    )


def _profile_applies(value: str) -> bool:
    normalized = (value or "").strip().casefold()
    return bool(normalized) and not any(token in normalized for token in ("no aplica", "no aplicable", "ninguno", "sin actividad"))


def profile_payload(profile: OrganizationCarbonProfile, organization: Organization) -> dict[str, Any]:
    processes = _json_list(profile.core_processes_json)
    process_text = " ".join(processes).casefold()
    sector_text = f"{organization.sector} {profile.sector_subsector}".casefold()
    process_emission_terms = ("cement", "cal", "quím", "ferment", "compost", "digest", "tratamiento", "fundición", "reacción")
    return {
        "employees": organization.employees,
        "company_size": profile.company_size,
        "sector": organization.sector,
        "facilities_count": len(organization.facilities),
        "countries_count": profile.countries_count,
        "core_processes": processes,
        "has_fleet": _profile_applies(profile.fleet_profile),
        "uses_fuels": bool(_json_list(profile.energy_sources_json)),
        "uses_refrigerants": _profile_applies(profile.refrigerants_profile),
        "manages_waste": _profile_applies(profile.waste_profile),
        "has_wastewater": _profile_applies(profile.wastewater_profile),
        "has_agriculture": _profile_applies(profile.agriculture_land_use_profile),
        "relies_on_suppliers": _profile_applies(profile.supplier_profile),
        "has_process_emissions": any(term in process_text or term in sector_text for term in process_emission_terms),
        "desired_scopes": "Alcances 1, 2 y 3 priorizado" if profile.supplier_profile.strip() else "Alcances 1 y 2",
        "objective": ", ".join(_json_list(profile.reporting_drivers_json)) or "Conocer la huella corporativa",
        "data_availability": profile.data_availability,
        "evidence_readiness": profile.evidence_readiness,
        "current_data_systems": _json_list(profile.current_data_systems_json),
        "inventory_history": profile.inventory_history,
        "has_previous_inventory": profile.inventory_history != "Sin inventario anterior",
        "reporting_frequency": profile.reporting_frequency,
        "assurance_ambition": profile.assurance_ambition,
        "inventory_owner": profile.inventory_owner,
        "executive_sponsor": profile.executive_sponsor,
    }


def update_carbon_profile(
    session: Session,
    organization: Organization,
    *,
    actor_email: str,
    payload: dict[str, Any],
) -> OrganizationCarbonProfile:
    profile = get_or_create_carbon_profile(session, organization.id)
    text_fields = (
        "company_size", "business_model", "sector_subsector", "operating_description",
        "fleet_profile", "refrigerants_profile", "waste_profile", "wastewater_profile",
        "agriculture_land_use_profile", "supplier_profile", "inventory_history",
        "data_availability", "evidence_readiness", "reporting_frequency",
        "assurance_ambition", "inventory_owner", "executive_sponsor", "status", "source",
    )
    for field in text_fields:
        if field in payload:
            setattr(profile, field, str(payload.get(field) or "").strip())
    profile.countries_count = max(1, int(payload.get("countries_count") or profile.countries_count or 1))
    json_fields = (
        "countries", "facility_types", "core_processes", "energy_sources", "key_materials",
        "reporting_drivers", "climate_goals", "current_data_systems",
    )
    for field in json_fields:
        if field in payload:
            setattr(profile, f"{field}_json", _dump(_json_list(payload.get(field))))
    completion_checks = [
        profile.business_model, profile.sector_subsector, profile.operating_description,
        profile.core_processes_json not in {"", "[]"}, profile.energy_sources_json not in {"", "[]"},
        profile.inventory_owner, profile.executive_sponsor, profile.data_availability,
        profile.evidence_readiness, profile.reporting_drivers_json not in {"", "[]"},
    ]
    profile.profile_completion = round(sum(bool(item) for item in completion_checks) / len(completion_checks) * 100)
    profile.status = "Completo" if profile.profile_completion >= 80 else "En construcción"
    profile.updated_by = actor_email
    profile.updated_at = datetime.now(UTC)
    add_audit(
        session, organization.id, actor_email, "ACTUALIZAR", "Perfil de carbono",
        organization.trade_name or organization.name,
        f"Completitud {profile.profile_completion}% · {profile.status}",
    )
    return profile


def create_assessment(
    session: Session,
    *,
    payload: dict[str, Any],
    organization_id: int | None = None,
    lead_id: int | None = None,
    actor_email: str = "motor-v045",
    is_demo: bool = False,
) -> DiagnosticAssessment:
    result = assess_company(payload)
    assessment = DiagnosticAssessment(
        organization_id=organization_id,
        lead_id=lead_id,
        assessment_code=f"DIA-{datetime.now(UTC).strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}",
        assessment_version="V0.45",
        status="Calculado",
        company_size_score=result.company_size_score,
        operational_complexity_score=result.operational_complexity_score,
        scope_complexity_score=result.scope_complexity_score,
        data_maturity_score=result.data_maturity_score,
        governance_maturity_score=result.governance_maturity_score,
        reporting_pressure_score=result.reporting_pressure_score,
        verification_readiness_score=result.verification_readiness_score,
        total_score=result.total_score,
        maturity_level=result.maturity_level,
        complexity_level=result.complexity_level,
        recommended_package_code=result.package_code,
        estimated_duration_months=result.duration_months,
        estimated_effort_hours=result.effort_hours,
        recommended_scopes_json=_dump(result.recommended_scopes),
        applicable_modules_json=_dump(result.applicable_modules),
        probable_sources_json=_dump(result.probable_sources),
        priority_scope3_categories_json=_dump(result.priority_scope3_categories),
        exclusions_json=_dump(result.exclusions),
        findings_json=_dump(result.findings),
        risk_flags_json=_dump(result.risk_flags),
        next_steps_json=_dump(result.next_steps),
        answers_json=_dump(payload),
        assessed_by=actor_email,
        is_demo=is_demo,
    )
    session.add(assessment)
    session.flush()
    if organization_id:
        organization = session.get(Organization, organization_id)
        add_audit(
            session, organization_id, actor_email, "EVALUAR", "Diagnóstico de carbono",
            organization.trade_name if organization else assessment.assessment_code,
            f"{result.complexity_level} · {result.maturity_level} · {PACKAGE_LABELS[result.package_code]}",
        )
    return assessment


def approve_assessment(
    session: Session,
    assessment: DiagnosticAssessment,
    *,
    actor_email: str,
    notes: str,
) -> DiagnosticAssessment:
    assessment.status = "Aprobado"
    assessment.approved_by = actor_email
    assessment.approved_at = datetime.now(UTC)
    assessment.approval_notes = notes.strip()
    if assessment.organization_id:
        add_audit(
            session, assessment.organization_id, actor_email, "APROBAR", "Diagnóstico de carbono",
            assessment.assessment_code,
            f"Paquete {PACKAGE_LABELS.get(assessment.recommended_package_code, assessment.recommended_package_code)}",
            reason=notes.strip(),
        )
    return assessment


def _add_months(base: date, months: int) -> date:
    return base + timedelta(days=max(months, 1) * 30)


def build_implementation_plan(
    session: Session,
    assessment: DiagnosticAssessment,
    *,
    actor_email: str,
    start_date: date | None = None,
    owner: str = "Equipo del inventario",
) -> ImplementationPlan:
    if not assessment.organization_id:
        raise ValueError("El diagnóstico debe estar vinculado a una organización para crear un plan.")
    existing = session.scalar(select(ImplementationPlan).where(ImplementationPlan.assessment_id == assessment.id))
    if existing:
        return existing
    start = start_date or date.today()
    package = assessment.recommended_package_code
    scopes = _json_list(assessment.recommended_scopes_json)
    plan = ImplementationPlan(
        organization_id=assessment.organization_id,
        assessment_id=assessment.id,
        code=f"PLAN-{assessment.assessment_code}",
        title=f"Plan de implementación · {PACKAGE_LABELS.get(package, package)}",
        status="Aprobado" if assessment.status == "Aprobado" else "Borrador",
        package_code=package,
        start_date=start,
        target_completion=_add_months(start, assessment.estimated_duration_months),
        duration_months=assessment.estimated_duration_months,
        scope_summary=" · ".join(scopes),
        success_criteria_json=_dump([
            "Límites y metodología aprobados",
            "Datos y evidencias con responsables definidos",
            "Cálculos reproducibles y controles de calidad cerrados",
            "Informe y plan de mejora aprobados por la organización",
        ]),
        owner=owner.strip() or "Equipo del inventario",
        created_by=actor_email,
        is_demo=assessment.is_demo,
    )
    session.add(plan)
    session.flush()

    advanced = package == "CORPORATIVO"
    business = package in {"EMPRESARIAL", "CORPORATIVO"}
    phases: list[tuple[str, str, str, str, str, list[str], int]] = [
        ("P1", "Diagnóstico y alcance", "Aprobar perfil, objetivo y paquete", "Confirmar límites, exclusiones, sedes, responsables y profundidad del servicio.", "/inteligencia-producto", ["Perfil validado", "Diagnóstico aprobado", "Plan aprobado"], 10),
        ("P2", "Diseño metodológico", "Configurar inventario y metodología", "Definir protocolo, consolidación, fuentes, unidades, factores y política de calidad.", "/metodologia", ["Inventario configurado", "Mapa de fuentes", "Criterios metodológicos"], 25),
        ("P3", "Datos y evidencias", "Ejecutar el plan de datos", "Solicitar, cargar, normalizar y validar datos y soportes por sede, fuente y periodo.", "/informacion", ["Plan de datos", "Evidencias", "Control de cobertura"], 55),
        ("P4", "Cálculo y control", "Calcular y resolver hallazgos", "Reproducir resultados, gestionar incertidumbre, observaciones y conciliación mensual.", "/calculos", ["Resultados por gas y fuente", "Control de calidad", "Observaciones resueltas"], 75),
        ("P5", "Cierre e informe", "Aprobar y reportar", "Cerrar el periodo, generar memoria técnica, informe ejecutivo y recomendaciones.", "/reportes", ["Cierre aprobado", "Memoria de cálculo", "Informe ejecutivo"], 92),
        ("P6", "Reducción y siguiente ciclo", "Convertir el inventario en decisiones", "Priorizar acciones, metas, indicadores y mejoras para el siguiente periodo.", "/reduccion", ["Portafolio de acciones", "Indicadores", "Hoja de ruta"], 100),
    ]
    if advanced:
        phases.insert(5, ("P5B", "Aseguramiento", "Preparar verificación independiente", "Consolidar paquete reproducible, hallazgos y respuestas para un tercero independiente.", "/verificacion", ["Paquete del verificador", "Hallazgos gestionados"], 88))
    elif not business:
        phases = [item for item in phases if item[0] not in {"P6"}] + [
            ("P6", "Mejora inicial", "Definir acciones inmediatas", "Seleccionar recomendaciones prácticas y un plan de ampliación para el siguiente periodo.", "/reduccion", ["Recomendaciones priorizadas"], 100)
        ]

    total_days = max(assessment.estimated_duration_months * 30, 30)
    for order, (phase_code, phase_name, title, description, route, deliverables, percent) in enumerate(phases, 1):
        due = start + timedelta(days=math.ceil(total_days * percent / 100))
        session.add(ImplementationPlanItem(
            plan_id=plan.id,
            phase_code=phase_code,
            phase_name=phase_name,
            title=title,
            description=description,
            status="Pendiente",
            owner=owner.strip() or "Equipo del inventario",
            due_date=due,
            dependencies_json="[]" if order == 1 else _dump([phases[order - 2][0]]),
            deliverables_json=_dump(deliverables),
            module_route=route,
            display_order=order,
            updated_by=actor_email,
        ))
    add_audit(
        session, assessment.organization_id, actor_email, "CREAR", "Plan de implementación",
        plan.code, f"{PACKAGE_LABELS.get(package, package)} · {assessment.estimated_duration_months} meses",
    )
    return plan


def assessment_view(assessment: DiagnosticAssessment | None) -> dict[str, Any] | None:
    if not assessment:
        return None
    return {
        "row": assessment,
        "package_label": PACKAGE_LABELS.get(assessment.recommended_package_code, assessment.recommended_package_code),
        "package_description": PACKAGE_DESCRIPTIONS.get(assessment.recommended_package_code, ""),
        "recommended_scopes": _json_list(assessment.recommended_scopes_json),
        "applicable_modules": _json_list(assessment.applicable_modules_json),
        "probable_sources": _json_list(assessment.probable_sources_json),
        "priority_scope3_categories": _json_list(assessment.priority_scope3_categories_json),
        "exclusions": _json_list(assessment.exclusions_json),
        "findings": _json_list(assessment.findings_json),
        "risk_flags": _json_list(assessment.risk_flags_json),
        "next_steps": _json_list(assessment.next_steps_json),
        "answers": json.loads(assessment.answers_json or "{}"),
    }


def plan_view(plan: ImplementationPlan) -> dict[str, Any]:
    return {
        "row": plan,
        "package_label": PACKAGE_LABELS.get(plan.package_code, plan.package_code),
        "success_criteria": _json_list(plan.success_criteria_json),
        "items": [
            {
                "row": item,
                "deliverables": _json_list(item.deliverables_json),
                "dependencies": _json_list(item.dependencies_json),
            }
            for item in plan.items
        ],
    }


def carbon_profile_view(profile: OrganizationCarbonProfile | None) -> dict[str, Any] | None:
    if not profile:
        return None
    return {
        "row": profile,
        "countries": ", ".join(_json_list(profile.countries_json)),
        "facility_types": ", ".join(_json_list(profile.facility_types_json)),
        "core_processes": ", ".join(_json_list(profile.core_processes_json)),
        "energy_sources": ", ".join(_json_list(profile.energy_sources_json)),
        "key_materials": ", ".join(_json_list(profile.key_materials_json)),
        "reporting_drivers": ", ".join(_json_list(profile.reporting_drivers_json)),
        "climate_goals": ", ".join(_json_list(profile.climate_goals_json)),
        "current_data_systems": ", ".join(_json_list(profile.current_data_systems_json)),
    }


def ensure_demo_product_intelligence(session: Session) -> dict[str, int]:
    """Create auditable V0.45 profiles, assessments and plans for the two demo companies."""
    specs: dict[str, dict[str, Any]] = {
        "Greenatics": {
            "profile": {
                "company_size": "Pequeña",
                "business_model": "Tratamiento y aprovechamiento de residuos orgánicos, producción de fertilizantes y servicios de consultoría ambiental.",
                "sector_subsector": "Gestión de residuos orgánicos, compostaje, digestión anaerobia y fertilizantes organominerales",
                "operating_description": "Operación multisede con recepción de residuos, tratamiento biológico, producción sólida y líquida, movimiento de materiales, consumo energético y distribución de productos.",
                "countries_count": 1,
                "countries": ["Colombia"],
                "facility_types": ["Planta de aprovechamiento", "Planta de fertilizantes", "Oficina administrativa"],
                "core_processes": ["Recepción de residuos", "Compostaje", "Digestión anaerobia", "Producción de fertilizantes", "Almacenamiento", "Distribución"],
                "energy_sources": ["Electricidad de red", "Diésel", "Gasolina", "Biogás"],
                "fleet_profile": "Vehículos y maquinaria de operación; parte del transporte es contratado.",
                "refrigerants_profile": "Aires acondicionados y equipos menores con control de recargas pendiente de estandarización.",
                "waste_profile": "Recepción, tratamiento, aprovechamiento y rechazos de residuos orgánicos.",
                "wastewater_profile": "Aguas de proceso, lixiviados y corrientes asociadas al tratamiento orgánico.",
                "agriculture_land_use_profile": "Aplicación de fertilizantes y evaluación de emisiones asociadas a nitrógeno y suelos en proyectos específicos.",
                "key_materials": ["Residuos orgánicos", "Urea", "Precursores minerales", "Empaques"],
                "supplier_profile": "Proveedores de materias primas, empaques, transporte y servicios técnicos con distinta madurez de información.",
                "reporting_drivers": ["Gestión interna", "Clientes", "Proyectos municipales", "Estrategia de reducción"],
                "climate_goals": ["Medir mensualmente", "Reducir consumos y fugas", "Demostrar aprovechamiento y circularidad"],
                "current_data_systems": ["Excel", "Bitácoras de planta", "Facturas", "SharePoint"],
                "inventory_history": "Inventario preliminar",
                "data_availability": "Media",
                "evidence_readiness": "Parcial",
                "reporting_frequency": "Mensual",
                "assurance_ambition": "Preparación para verificación limitada",
                "inventory_owner": "Dirección administrativa y equipo ambiental",
                "executive_sponsor": "Gerencia general",
                "source": "Demo certificado V0.45",
            },
            "assessment": {
                "desired_scopes": "Alcances 1, 2 y 3 avanzado",
                "objective": "Requisito de clientes y estrategia de reducción",
                "urgency": "Alta",
                "deadline_months": 6,
            },
        },
        "Industrias Andinas": {
            "profile": {
                "company_size": "Mediana",
                "business_model": "Manufactura y comercialización de productos industriales con abastecimiento intensivo en materiales y logística.",
                "sector_subsector": "Manufactura química y transformación industrial",
                "operating_description": "Tres sedes con producción, caldera, refrigeración, flota, bodegas, compras estratégicas y transporte contratado.",
                "countries_count": 1,
                "countries": ["Colombia"],
                "facility_types": ["Planta industrial", "Bodega", "Oficina"],
                "core_processes": ["Producción", "Generación de vapor", "Refrigeración", "Almacenamiento", "Distribución"],
                "energy_sources": ["Electricidad de red", "Diésel", "Gasolina"],
                "fleet_profile": "Flota corporativa y transporte contratado para materias primas y producto terminado.",
                "refrigerants_profile": "Equipos de climatización y refrigeración con inventario anual de recargas.",
                "waste_profile": "Residuos ordinarios, aprovechables y corrientes de proceso entregadas a gestores.",
                "wastewater_profile": "Vertimientos industriales y domésticos con medición parcial.",
                "agriculture_land_use_profile": "No aplica directamente.",
                "key_materials": ["Acero", "Químicos", "Empaques", "Combustibles"],
                "supplier_profile": "Proveedores estratégicos de acero, químicos, empaques y transporte; campaña de alcance 3 activa.",
                "reporting_drivers": ["Clientes", "Reporte de sostenibilidad", "Preparación para verificación"],
                "climate_goals": ["Reducir 20% al 2030", "Eficiencia térmica", "Energía solar", "Control de fugas"],
                "current_data_systems": ["ERP", "Excel", "Facturación", "Registros de mantenimiento"],
                "inventory_history": "Serie histórica",
                "data_availability": "Alta",
                "evidence_readiness": "Media",
                "reporting_frequency": "Mensual",
                "assurance_ambition": "Preparación para verificación razonable",
                "inventory_owner": "Coordinación ambiental",
                "executive_sponsor": "Gerencia de operaciones",
                "source": "Demo certificado V0.45",
            },
            "assessment": {
                "desired_scopes": "Alcances 1, 2 y 3 avanzado",
                "objective": "Preparación para verificación",
                "urgency": "Normal",
                "deadline_months": 8,
            },
        },
    }
    created_profiles = created_assessments = created_plans = 0
    for trade_name, spec in specs.items():
        organization = session.scalar(select(Organization).where(Organization.trade_name == trade_name))
        if not organization:
            continue
        existing_profile = get_or_create_carbon_profile(session, organization.id)
        was_blank = existing_profile.profile_completion == 0
        profile = update_carbon_profile(
            session,
            organization,
            actor_email="sistema-demo-v045",
            payload=spec["profile"],
        )
        if was_blank:
            created_profiles += 1
        assessment = session.scalar(
            select(DiagnosticAssessment)
            .where(
                DiagnosticAssessment.organization_id == organization.id,
                DiagnosticAssessment.assessment_version == "V0.45",
                DiagnosticAssessment.is_demo.is_(True),
            )
            .order_by(DiagnosticAssessment.id.desc())
            .limit(1)
        )
        if not assessment:
            payload = profile_payload(profile, organization)
            payload.update(spec["assessment"])
            assessment = create_assessment(
                session,
                payload=payload,
                organization_id=organization.id,
                actor_email="sistema-demo-v045",
                is_demo=True,
            )
            approve_assessment(
                session,
                assessment,
                actor_email="comite-demo-v045",
                notes="Aprobación demostrativa para recorrer la plataforma; no constituye validación externa.",
            )
            created_assessments += 1
        plan = session.scalar(select(ImplementationPlan).where(ImplementationPlan.assessment_id == assessment.id))
        if not plan:
            build_implementation_plan(
                session,
                assessment,
                actor_email="sistema-demo-v045",
                start_date=date(2026, 8, 1),
                owner=profile.inventory_owner or "Equipo del inventario",
            )
            created_plans += 1
    session.flush()
    return {
        "profiles": created_profiles,
        "assessments": created_assessments,
        "plans": created_plans,
    }
