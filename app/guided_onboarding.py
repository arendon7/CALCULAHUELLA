from __future__ import annotations

"""Guided onboarding decision engine for V0.52.

The module stores the customer's initial decisions in ``PlatformSetting`` and
projects them into the existing carbon profile. It does not introduce a new
persistence structure and it never changes calculations or emission factors.
"""

from dataclasses import dataclass
from datetime import date
import json
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import Organization, OrganizationCarbonProfile, PlatformSetting
from .inventory_starters import get_starter_pack, starter_pack_catalog

SETTING_KEY = "guided_onboarding_v052"
SETTING_DESCRIPTION = "Decisiones del asistente inicial V0.52"


@dataclass(frozen=True)
class Option:
    code: str
    label: str
    description: str


OBJECTIVES: tuple[Option, ...] = (
    Option("baseline", "Construir una línea base confiable", "Conocer las emisiones actuales y establecer un punto de comparación reproducible."),
    Option("management", "Gestionar y reducir emisiones", "Priorizar fuentes relevantes, metas e iniciativas de reducción con responsables."),
    Option("client", "Responder a clientes o cadenas de valor", "Entregar información trazable para solicitudes comerciales, proveedores o licitaciones."),
    Option("reporting", "Preparar un reporte corporativo", "Consolidar resultados, límites y evidencia para comunicación interna o externa controlada."),
    Option("verification", "Prepararse para revisión o verificación", "Elevar la calidad documental y metodológica antes de una evaluación independiente."),
    Option("requirement", "Atender un requisito específico", "Organizar el inventario alrededor de una exigencia contractual, normativa o financiera."),
)

SECTOR_FAMILIES: tuple[Option, ...] = (
    Option("services", "Servicios y oficinas", "Operaciones administrativas, profesionales, comerciales o institucionales."),
    Option("productive", "Industria y operación productiva", "Manufactura, plantas, talleres, logística o procesos con consumo material y energético."),
    Option("agro", "Agropecuario y uso del suelo", "Agricultura, ganadería, silvicultura, fertilización, cambio de uso del suelo o agroindustria."),
    Option("waste", "Residuos, aseo y valorización", "Recolección, transporte, tratamiento, compostaje, biogás, reciclaje o disposición."),
    Option("custom", "Perfil mixto o especializado", "Operación que requiere una delimitación técnica particular antes de definir fuentes."),
)

SCOPE_AMBITIONS: tuple[Option, ...] = (
    Option("essential", "Alcances 1 y 2 primero", "Prioriza emisiones directas y electricidad adquirida para construir una base controlable."),
    Option("prioritized", "Alcances 1, 2 y alcance 3 priorizado", "Incluye las categorías indirectas con mayor relevancia para el objetivo y el sector."),
    Option("advanced", "Cobertura amplia y preparación para aseguramiento", "Busca una cobertura extensa, reglas formales y evidencia suficiente para revisión independiente."),
)

READINESS_OPTIONS: tuple[Option, ...] = (
    Option("low", "Inicial", "Los datos están dispersos, son manuales o todavía no tienen responsables claros."),
    Option("medium", "Intermedia", "Existen registros, pero requieren conciliación, normalización o evidencia adicional."),
    Option("high", "Avanzada", "Los datos tienen responsables, periodicidad, sistemas de origen y soportes consistentes."),
)

DATA_SYSTEM_OPTIONS: tuple[Option, ...] = (
    Option("spreadsheets", "Hojas de cálculo", "Archivos Excel, CSV o controles manuales."),
    Option("accounting", "Sistema contable o ERP", "Compras, facturas, inventarios o consumos registrados en sistemas empresariales."),
    Option("meters", "Medidores y registros operativos", "Lecturas de energía, combustibles, producción, básculas o control de procesos."),
    Option("providers", "Información de proveedores", "Certificados, reportes logísticos, gestores, comercializadores o terceros."),
    Option("documents", "Documentos sin estructurar", "Facturas, PDF, correos, contratos o soportes que deben organizarse."),
)

FREQUENCIES = ("Mensual", "Trimestral", "Semestral", "Anual")
ASSURANCE_OPTIONS = (
    "Uso interno sin verificación externa",
    "Revisión técnica dirigida",
    "Preparación para verificación limitada",
    "Preparación para verificación razonable",
)


def _option_map(options: Iterable[Option]) -> dict[str, Option]:
    return {item.code: item for item in options}


OBJECTIVE_MAP = _option_map(OBJECTIVES)
SECTOR_MAP = _option_map(SECTOR_FAMILIES)
SCOPE_MAP = _option_map(SCOPE_AMBITIONS)
READINESS_MAP = _option_map(READINESS_OPTIONS)
DATA_SYSTEM_MAP = _option_map(DATA_SYSTEM_OPTIONS)


def infer_sector_family(sector: str) -> str:
    value = str(sector or "").strip().casefold()
    if any(token in value for token in ("resid", "aseo", "recicl", "compost", "biog", "waste", "saneamiento")):
        return "waste"
    if any(token in value for token in ("agro", "agric", "ganad", "pecuar", "forest", "cultivo", "alimento")):
        return "agro"
    if any(token in value for token in ("industr", "manufact", "planta", "produ", "construc", "logíst", "logist", "minería", "mineria")):
        return "productive"
    if any(token in value for token in ("serv", "consult", "comerc", "educ", "salud", "financ", "tecnolog", "administr")):
        return "services"
    return "custom"


def default_profile(organization: Organization, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    return {
        "objective": "baseline",
        "reporting_driver": "Gestión interna y toma de decisiones",
        "success_definition": "Contar con un inventario trazable, revisado y útil para priorizar acciones.",
        "sector_family": infer_sector_family(organization.sector),
        "operating_description": "",
        "scope_ambition": "prioritized",
        "reporting_frequency": "Anual",
        "assurance_ambition": "Revisión técnica dirigida",
        "data_readiness": "medium",
        "evidence_readiness": "medium",
        "data_systems": ["spreadsheets", "documents"],
        "inventory_owner": organization.contact_name or "Responsable del inventario",
        "executive_sponsor": "Dirección o gerencia",
        "period_start": date(today.year, 1, 1).isoformat(),
        "period_end": date(today.year, 12, 31).isoformat(),
        "notes": "",
        "saved": False,
    }


def load_profile(session: Session, organization: Organization) -> dict[str, Any]:
    profile = default_profile(organization)
    row = session.scalar(
        select(PlatformSetting).where(
            PlatformSetting.organization_id == organization.id,
            PlatformSetting.key == SETTING_KEY,
        )
    )
    if not row or not row.value:
        return profile
    try:
        stored = json.loads(row.value)
    except (TypeError, ValueError):
        return profile
    if isinstance(stored, dict):
        profile.update(stored)
        profile["saved"] = True
    return profile


def profile_completion(profile: dict[str, Any]) -> int:
    if not profile.get("saved"):
        return 0
    required = (
        "objective",
        "reporting_driver",
        "success_definition",
        "sector_family",
        "operating_description",
        "scope_ambition",
        "reporting_frequency",
        "assurance_ambition",
        "data_readiness",
        "evidence_readiness",
        "inventory_owner",
        "executive_sponsor",
        "period_start",
        "period_end",
    )
    completed = sum(1 for key in required if str(profile.get(key, "")).strip())
    systems = profile.get("data_systems") or []
    completed += 1 if systems else 0
    return round(completed / (len(required) + 1) * 100)


def save_profile(
    session: Session,
    organization: Organization,
    payload: dict[str, Any],
    *,
    actor_email: str,
) -> dict[str, Any]:
    profile = default_profile(organization)
    profile.update(payload)
    profile["saved"] = True
    score = profile_completion(profile)
    profile["completion"] = score

    row = session.scalar(
        select(PlatformSetting).where(
            PlatformSetting.organization_id == organization.id,
            PlatformSetting.key == SETTING_KEY,
        )
    )
    if not row:
        row = PlatformSetting(
            organization_id=organization.id,
            key=SETTING_KEY,
            value_type="json",
            description=SETTING_DESCRIPTION,
        )
        session.add(row)
    row.value = json.dumps(profile, ensure_ascii=False, sort_keys=True)
    row.updated_by = actor_email

    carbon_profile = session.scalar(
        select(OrganizationCarbonProfile).where(OrganizationCarbonProfile.organization_id == organization.id)
    )
    if not carbon_profile:
        carbon_profile = OrganizationCarbonProfile(organization_id=organization.id)
        session.add(carbon_profile)
    carbon_profile.sector_subsector = organization.sector
    carbon_profile.operating_description = str(profile.get("operating_description", "")).strip()
    carbon_profile.reporting_drivers_json = json.dumps(
        [
            OBJECTIVE_MAP.get(str(profile.get("objective")), OBJECTIVE_MAP["baseline"]).label,
            str(profile.get("reporting_driver", "")).strip(),
        ],
        ensure_ascii=False,
    )
    carbon_profile.current_data_systems_json = json.dumps(profile.get("data_systems") or [], ensure_ascii=False)
    carbon_profile.data_availability = READINESS_MAP.get(str(profile.get("data_readiness")), READINESS_MAP["medium"]).label
    carbon_profile.evidence_readiness = READINESS_MAP.get(str(profile.get("evidence_readiness")), READINESS_MAP["medium"]).label
    carbon_profile.reporting_frequency = str(profile.get("reporting_frequency") or "Anual")
    carbon_profile.assurance_ambition = str(profile.get("assurance_ambition") or ASSURANCE_OPTIONS[0])
    carbon_profile.inventory_owner = str(profile.get("inventory_owner", "")).strip()
    carbon_profile.executive_sponsor = str(profile.get("executive_sponsor", "")).strip()
    carbon_profile.profile_completion = score
    carbon_profile.status = "Completo" if score >= 85 else "Borrador"
    carbon_profile.source = "Asistente inicial V0.52"
    carbon_profile.updated_by = actor_email
    return profile


def recommended_starter_pack(sector_family: str) -> str:
    return {
        "services": "services",
        "productive": "productive",
        "agro": "agro",
        "waste": "waste",
        "custom": "custom",
    }.get(sector_family, "custom")


def _scope_recommendation(profile: dict[str, Any], sector_family: str) -> list[str]:
    ambition = str(profile.get("scope_ambition") or "prioritized")
    scopes = ["Alcance 1", "Alcance 2"]
    if ambition in {"prioritized", "advanced"}:
        scopes.append("Alcance 3 priorizado")
    if ambition == "advanced":
        scopes.append("Categorías adicionales justificadas por materialidad y objetivo")
    if sector_family == "agro":
        scopes.append("Fuentes agropecuarias, fertilización y uso del suelo evaluadas por separado")
    if sector_family == "waste":
        scopes.append("Tratamiento, transporte y emisiones evitadas separados para evitar compensaciones implícitas")
    return scopes


def _methodology_recommendation(profile: dict[str, Any]) -> dict[str, str]:
    objective = str(profile.get("objective") or "baseline")
    scope_ambition = str(profile.get("scope_ambition") or "prioritized")
    assurance = str(profile.get("assurance_ambition") or "")
    if objective == "verification" or "verificación" in assurance.casefold() or scope_ambition == "advanced":
        return {
            "methodology": "GHG Protocol + ISO 14064-1",
            "methodology_version": "GHG Protocol Corporate Standard · ISO 14064-1:2018",
            "gwp_version": "IPCC AR6 · 100 años",
            "consolidation_approach": "Control operacional",
            "materiality_threshold": "3",
            "review_level": "Revisión metodológica reforzada y trazabilidad preparada para aseguramiento",
        }
    return {
        "methodology": "GHG Protocol + ISO 14064-1",
        "methodology_version": "GHG Protocol Corporate Standard · ISO 14064-1:2018",
        "gwp_version": "IPCC AR6 · 100 años",
        "consolidation_approach": "Control operacional",
        "materiality_threshold": "5",
        "review_level": "Revisión técnica dirigida antes de comunicar resultados",
    }


def _sector_notes(sector_family: str) -> list[str]:
    return {
        "services": [
            "No limitar el análisis a electricidad: revisar movilidad, viajes, residuos y compras relevantes.",
            "Definir una unidad funcional útil, por ejemplo empleado, sede, ingreso o servicio prestado.",
        ],
        "productive": [
            "Conciliar energía, combustibles, producción y balance de materiales en el mismo periodo.",
            "Separar emisiones de combustión, proceso, refrigerantes, transporte y materias primas.",
        ],
        "agro": [
            "Distinguir fertilización, manejo de suelos, fermentación, estiércol, energía y cambio de uso del suelo.",
            "Definir unidades productivas y espaciales consistentes: hectárea, tonelada, animal o lote.",
        ],
        "waste": [
            "Separar emisiones brutas del tratamiento de cualquier estimación de emisiones evitadas.",
            "Conservar balances de masa, pesajes, rutas, rechazos, biogás y destino final por periodo.",
        ],
        "custom": [
            "Realizar una sesión de delimitación antes de cerrar las fuentes y categorías aplicables.",
            "Documentar procesos, sedes, activos y relaciones de control para evitar vacíos de cobertura.",
        ],
    }.get(sector_family, [])


def decision_plan(
    profile: dict[str, Any],
    organization: Organization,
    *,
    inventory: Any | None = None,
) -> dict[str, Any]:
    sector_family = str(profile.get("sector_family") or infer_sector_family(organization.sector))
    objective = OBJECTIVE_MAP.get(str(profile.get("objective")), OBJECTIVE_MAP["baseline"])
    sector = SECTOR_MAP.get(sector_family, SECTOR_MAP["custom"])
    scope = SCOPE_MAP.get(str(profile.get("scope_ambition")), SCOPE_MAP["prioritized"])
    methodology = _methodology_recommendation(profile)
    pack_code = recommended_starter_pack(sector_family)
    pack = get_starter_pack(pack_code)
    score = profile_completion(profile)

    route = [
        {"number": 1, "title": "Propósito", "status": "Listo" if profile.get("objective") else "Pendiente", "route": "/onboarding/guiado", "result": objective.label},
        {"number": 2, "title": "Perfil sectorial", "status": "Listo" if profile.get("operating_description") else "Pendiente", "route": "/onboarding/guiado", "result": sector.label},
        {"number": 3, "title": "Metodología", "status": "Listo" if inventory and inventory.methodology else "Recomendado", "route": f"/inventarios/{inventory.id}/editar" if inventory else "/onboarding/guiado", "result": methodology["methodology"]},
        {"number": 4, "title": "Inventario y límites", "status": "Listo" if inventory else "Pendiente", "route": f"/inventarios/{inventory.id}" if inventory else "/onboarding/guiado", "result": "Periodo y operaciones incluidas"},
        {"number": 5, "title": "Fuentes", "status": "Listo" if inventory and inventory.sources else "Pendiente", "route": f"/inventarios/{inventory.id}/fuentes" if inventory else "/onboarding/guiado", "result": pack.name if pack else "Mapa personalizado"},
        {"number": 6, "title": "Datos y evidencias", "status": "En curso" if inventory and any(source.activity_records for source in inventory.sources) else "Pendiente", "route": "/captura-guiada", "result": "Responsables, unidades, periodos y soportes"},
        {"number": 7, "title": "Factores", "status": "Pendiente", "route": "/metodologia", "result": "Selección, compatibilidad y aprobación técnica"},
        {"number": 8, "title": "Cálculo", "status": "En curso" if inventory and any(source.emissions for source in inventory.sources) else "Pendiente", "route": "/calculos", "result": "Resultado reproducible por dato, factor y gas"},
        {"number": 9, "title": "Revisión e informe", "status": "Pendiente", "route": "/entrega-profesional", "result": "Limitaciones, hallazgos y paquete documental"},
        {"number": 10, "title": "Reducción", "status": "Pendiente", "route": "/reduccion", "result": "Metas y portafolio de medidas, separado del inventario bruto"},
    ]

    next_step = next((item for item in route if item["status"] == "Pendiente"), route[-1])
    return {
        "completion": score,
        "ready_to_apply": score >= 75,
        "objective": {"code": objective.code, "label": objective.label, "description": objective.description},
        "sector": {"code": sector.code, "label": sector.label, "description": sector.description},
        "scope": {"code": scope.code, "label": scope.label, "description": scope.description},
        "scopes": _scope_recommendation(profile, sector_family),
        "methodology": methodology,
        "starter_pack": {
            "code": pack_code,
            "name": pack.name if pack else "Configuración personalizada",
            "summary": pack.summary if pack else "La matriz debe definirse mediante revisión sectorial.",
            "source_count": len(pack.sources) if pack else 0,
        },
        "sector_notes": _sector_notes(sector_family),
        "route": route,
        "next_step": next_step,
        "deliverable": {
            "title": {
                "baseline": "Inventario corporativo y línea base",
                "management": "Inventario y plan inicial de reducción",
                "client": "Paquete de información para clientes",
                "reporting": "Informe corporativo de emisiones",
                "verification": "Paquete técnico preparado para revisión independiente",
                "requirement": "Inventario orientado al requisito declarado",
            }.get(objective.code, "Inventario corporativo"),
            "success_definition": str(profile.get("success_definition", "")).strip(),
            "review_level": methodology["review_level"],
        },
        "data_system_labels": [
            DATA_SYSTEM_MAP[code].label for code in (profile.get("data_systems") or []) if code in DATA_SYSTEM_MAP
        ],
        "packs": starter_pack_catalog(),
    }


def data_checklist(profile: dict[str, Any], organization: Organization) -> list[dict[str, str]]:
    plan = decision_plan(profile, organization)
    pack = get_starter_pack(plan["starter_pack"]["code"])
    if not pack:
        return [
            {
                "source": "Mapa sectorial por definir",
                "scope": "Por definir",
                "category": "Delimitación técnica",
                "frequency": str(profile.get("reporting_frequency") or "Anual"),
                "unit": "Por definir",
                "evidence": "Mapa de procesos, sedes, activos y responsables",
                "owner": str(profile.get("inventory_owner") or "Responsable del inventario"),
                "priority": "Alta",
            }
        ]
    return [
        {
            "source": source.name,
            "scope": f"Alcance {source.scope}",
            "category": source.category,
            "frequency": source.data_frequency,
            "unit": source.preferred_unit,
            "evidence": source.evidence_hint,
            "owner": str(profile.get("inventory_owner") or "Responsable del inventario"),
            "priority": source.materiality,
        }
        for source in pack.sources
    ]
