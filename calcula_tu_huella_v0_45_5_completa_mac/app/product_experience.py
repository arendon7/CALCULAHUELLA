from __future__ import annotations

"""Role-oriented product experience with V0.32 methodological closure.

The platform keeps every existing route and capability. This module only
controls how that breadth is presented so the inventory workflow remains the
primary product and advanced/internal functions do not overwhelm daily users.
"""

from typing import Any

VIEW_MODES = {"essential", "complete"}

ROLE_PROFILES: dict[str, dict[str, str]] = {
    "Administrador": {
        "name": "Dirección y gobierno",
        "mission": "Supervisa el portafolio, destraba decisiones y asegura que el inventario avance con control.",
        "focus": "Avance, riesgos, aprobaciones y resultados para decisión.",
    },
    "Consultor": {
        "name": "Consultoría metodológica",
        "mission": "Configura el inventario, gobierna factores y acompaña el cierre técnico de principio a fin.",
        "focus": "Límites, datos, cálculo, calidad y entregables.",
    },
    "Cliente": {
        "name": "Responsable de información",
        "mission": "Entrega datos y evidencias confiables y responde las solicitudes del equipo del inventario.",
        "focus": "Pendientes, soportes, calidad y avance del periodo.",
    },
    "Revisor": {
        "name": "Revisión independiente",
        "mission": "Evalúa trazabilidad, calidad y consistencia antes de recomendar la aprobación.",
        "focus": "Hallazgos, factores, evidencias y puertas de cierre.",
    },
    "Verificador": {
        "name": "Verificación externa",
        "mission": "Reproduce la evidencia, documenta hallazgos y valida las respuestas de la organización.",
        "focus": "Paquete verificable, metodología, cálculos y hallazgos.",
    },
}


def _item(
    label: str,
    href: str,
    active: str,
    icon: str,
    *,
    any_capability: tuple[str, ...] = (),
    roles: tuple[str, ...] = (),
) -> dict[str, object]:
    return {
        "label": label,
        "href": href,
        "active": active,
        "icon": icon,
        "any_capability": any_capability,
        "roles": roles,
    }


CORE_SECTIONS: tuple[dict[str, object], ...] = (
    {
        "label": "INICIO",
        "items": (
            _item("Mi trabajo", "/dashboard", "dashboard", "⌂"),
            _item("Puesta en marcha", "/onboarding", "onboarding", "▶"),
            _item("Perfil y diagnóstico", "/inteligencia-producto", "product_intelligence", "◎", any_capability=("manage_org", "view_methodology", "manage_portfolio", "view_consolidation")),
            _item("Recorrido del inventario", "/recorrido-inventario", "journey", "→"),
        ),
    },
    {
        "label": "INVENTARIO",
        "items": (
            _item("Inventarios", "/inventarios", "inventories", "◔"),
            _item("Fuentes de emisión", "/inventario", "sources", "⌁"),
        ),
    },
    {
        "label": "DATOS Y EVIDENCIAS",
        "items": (
            _item("Datos y evidencias", "/informacion", "information", "▦"),
            _item(
                "Cargas operativas",
                "/cargas-operativas",
                "operational_imports",
                "⇩",
                any_capability=("provide_data", "manage_sources", "review", "approve", "view_methodology"),
            ),
            _item(
                "Calidad de datos",
                "/calidad-datos",
                "data_quality",
                "✓",
                any_capability=("provide_data", "manage_sources", "review", "approve", "view_methodology"),
            ),
            _item(
                "Cierre mensual",
                "/cierre-mensual",
                "period_close",
                "▣",
                any_capability=("provide_data", "manage_sources", "review", "approve", "view_methodology"),
            ),
        ),
    },
    {
        "label": "RESULTADOS Y CIERRE",
        "items": (
            _item("Motor y resultados", "/calculos", "calculations", "∑"),
            _item("Revisión y auditoría", "/control", "control", "◇"),
            _item("Cierre metodológico", "/metodologia/cierre", "methodology_closure", "◎", any_capability=("view_methodology", "review", "approve")),
            _item("Informes", "/reportes", "reports", "▤"),
            _item(
                "Portal del verificador",
                "/verificacion",
                "verification",
                "◈",
                any_capability=("external_audit", "review", "approve"),
            ),
        ),
    },
    {
        "label": "REDUCCIÓN",
        "items": (
            _item("Análisis", "/analisis", "analysis", "⌁"),
            _item("Plan de reducción", "/reduccion", "reduction", "↘"),
        ),
    },
)

ADVANCED_SECTIONS: tuple[dict[str, object], ...] = (
    {
        "label": "METODOLOGÍA",
        "items": (
            _item("Metodología", "/metodologia", "methodology", "⌘", any_capability=("view_methodology",)),
            _item("Núcleo metodológico", "/metodologia/nucleo", "methodology_core", "◈", any_capability=("view_methodology",)),
            _item("Biblioteca Colombia", "/metodologia/colombia", "colombia_library", "CO", any_capability=("view_methodology",)),
            _item("Gobierno metodológico", "/gobierno-metodologico", "methodology_governance", "◫", any_capability=("manage_methodology_governance",)),
            _item("Modelo sectorial", "/sectorizacion", "sectorization", "◎"),
        ),
    },
    {
        "label": "CAPACIDADES AVANZADAS",
        "items": (
            _item("Cadena de valor", "/cadena-valor", "supply_chain", "♧", any_capability=("manage_supply_chain", "review", "approve")),
            _item("Escenarios y MACC", "/escenarios", "scenarios", "◒"),
            _item("Inteligencia de impacto", "/inteligencia-impacto", "impact", "◉", any_capability=("view_impact", "manage_impact")),
            _item("Riesgos climáticos", "/riesgos-climaticos", "climate_risk", "△", any_capability=("view_climate_risk", "manage_climate_risk")),
            _item("Divulgación climática", "/divulgacion-climatica", "climate_disclosure", "◫", any_capability=("view_climate_disclosure", "manage_climate_disclosure")),
            _item("Cumplimiento", "/cumplimiento", "compliance", "✓", any_capability=("view_compliance", "manage_compliance")),
            _item("Centro documental", "/centro-documental", "documents", "▤", any_capability=("manage_documents",)),
        ),
    },
    {
        "label": "PILOTO GREENATICS",
        "items": (
            _item("Matriz del piloto", "/piloto-greenatics", "greenatics_pilot", "♻", any_capability=("view_methodology", "provide_data", "manage_sources")),
            _item("Ejecución del piloto", "/piloto-greenatics/ejecucion", "greenatics_pilot_execution", "▶", any_capability=("view_methodology", "provide_data", "manage_sources")),
        ),
    },
)

INTERNAL_SECTIONS: tuple[dict[str, object], ...] = (
    {
        "label": "ORGANIZACIÓN Y SERVICIO",
        "items": (
            _item("Organización", "/organizacion", "organization", "▥", any_capability=("manage_org",)),
            _item("Usuarios y roles", "/usuarios", "users", "♙", any_capability=("manage_org",)),
            _item("Portafolio multiempresa", "/portafolio", "portfolio", "▦", any_capability=("manage_portfolio",)),
            _item("Entorno demo", "/entorno-demo", "demo_environment", "◉", any_capability=("manage_portfolio",)),
            _item("Dirección ejecutiva", "/direccion-ejecutiva", "executive", "◉", any_capability=("manage_portfolio",)),
            _item("Cuenta y plan", "/cuenta-servicio", "service_account", "◌"),
            _item("Soporte", "/soporte", "support", "?", any_capability=("manage_support",)),
        ),
    },
    {
        "label": "OPERACIÓN INTERNA",
        "items": (
            _item("Gestión comercial", "/comercial", "commercial", "◇", any_capability=("manage_commercial",)),
            _item("Contratos y cartera", "/operacion-comercial", "commercial_operations", "▧", any_capability=("manage_commercial",)),
            _item("Éxito del cliente", "/exito-cliente", "customer_success", "♡", any_capability=("view_customer_success", "manage_customer_success")),
            _item("Integraciones", "/integraciones", "integrations", "⇄", any_capability=("manage_integrations",)),
            _item("Automatizaciones", "/automatizaciones", "automations", "◴", any_capability=("manage_automations",)),
            _item("Administración de plataforma", "/administracion-plataforma", "platform_admin", "⌬", any_capability=("manage_operations",)),
            _item("Operación y seguridad", "/operacion", "operations", "⚙", any_capability=("manage_operations",)),
            _item("Administración SaaS", "/administracion-saas", "saas_admin", "▣", any_capability=("manage_saas",)),
            _item("Alistamiento comercial", "/alistamiento", "readiness", "◆", any_capability=("manage_readiness",)),
            _item("Mapa del producto", "/modulos", "modules", "◫", any_capability=("manage_org", "view_methodology")),
            _item("Consolidación V1.0", "/consolidacion", "consolidation", "◆", any_capability=("view_consolidation", "manage_consolidation")),
        ),
    },
)


def role_profile(role: str) -> dict[str, str]:
    return dict(ROLE_PROFILES.get(role, ROLE_PROFILES["Cliente"]))


def normalize_view_mode(value: object) -> str:
    mode = str(value or "essential").strip().lower()
    return mode if mode in VIEW_MODES else "essential"


def _allowed(item: dict[str, object], role: str, capabilities: set[str]) -> bool:
    roles = set(item.get("roles") or ())
    if roles and role not in roles:
        return False
    required_any = set(item.get("any_capability") or ())
    return not required_any or bool(required_any & capabilities)


def _filter_sections(sections: tuple[dict[str, object], ...], role: str, capabilities: set[str]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for section in sections:
        items = [dict(item) for item in section["items"] if _allowed(item, role, capabilities)]
        if items:
            result.append({"label": section["label"], "items": items})
    return result


def navigation_for(user: dict[str, Any], mode: str) -> dict[str, object]:
    role = str(user.get("role", "Cliente"))
    capabilities = set(user.get("capabilities") or set())
    normalized = normalize_view_mode(mode)
    return {
        "mode": normalized,
        "core": _filter_sections(CORE_SECTIONS, role, capabilities),
        "advanced": _filter_sections(ADVANCED_SECTIONS, role, capabilities) if normalized == "complete" else [],
        "internal": _filter_sections(INTERNAL_SECTIONS, role, capabilities) if normalized == "complete" else [],
        "has_complete_view": bool(_filter_sections(ADVANCED_SECTIONS + INTERNAL_SECTIONS, role, capabilities)),
    }


def journey_detail(workspace: dict[str, Any], role: str) -> dict[str, Any]:
    """Transform the dashboard milestones into a decision-oriented journey."""
    owners = {
        "Configurar": "Consultor / administrador",
        "Recolectar": "Responsables de datos",
        "Calcular": "Consultor metodológico",
        "Revisar": "Revisor / aprobador",
        "Reportar": "Consultor / dirección",
    }
    descriptions = {
        "Configurar": "Definir periodo, límites, metodología, sedes y responsables.",
        "Recolectar": "Completar datos mensuales y evidencias con controles de calidad.",
        "Calcular": "Asignar factores vigentes y reproducir los resultados por fuente y gas.",
        "Revisar": "Resolver observaciones, conciliar periodos y aprobar el inventario.",
        "Reportar": "Emitir memoria de cálculo e informes para decisión y verificación.",
    }
    steps: list[dict[str, Any]] = []
    first_pending_found = False
    for index, milestone in enumerate(workspace.get("milestones", []), start=1):
        item = dict(milestone)
        item["number"] = index
        item["owner"] = owners.get(item["name"], "Equipo del inventario")
        item["description"] = descriptions.get(item["name"], item.get("detail", ""))
        item["current"] = not item.get("done", False) and not first_pending_found
        if item["current"]:
            first_pending_found = True
        steps.append(item)
    if not first_pending_found and steps:
        steps[-1]["current"] = True
    return {
        "role": role,
        "profile": role_profile(role),
        "steps": steps,
        "score": workspace.get("score", 0),
        "completed": workspace.get("completed", 0),
        "total": workspace.get("total", len(steps)),
        "actions": workspace.get("actions", []),
        "ready": bool(steps) and all(item.get("done") for item in steps),
    }
