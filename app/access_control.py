from __future__ import annotations

from urllib.parse import urlsplit

"""Centralized role/capability policy for the web application.

V0.21 moves authorization metadata out of the HTTP controller so the policy can
be audited and tested independently. Route-level checks remain mandatory.
"""

ROLE_ORDER = ["Administrador", "Consultor", "Cliente", "Revisor", "Verificador"]

ROLE_CAPABILITIES: dict[str, set[str]] = {
    "Administrador": {
        "manage_org", "manage_inventory", "manage_sources", "manage_supply_chain",
        "manage_operations", "manage_automations", "manage_integrations", "manage_portfolio",
        "manage_compliance", "view_compliance", "manage_documents",
        "manage_methodology_governance", "manage_readiness", "manage_subscription",
        "manage_support", "manage_saas", "manage_commercial", "manage_customer_success",
        "view_customer_success", "manage_impact", "view_impact", "manage_climate_risk",
        "view_climate_risk", "manage_climate_disclosure", "view_climate_disclosure",
        "manage_consolidation", "view_consolidation", "review", "approve", "view_methodology",
        "manage_workflow", "execute_workflow", "validate_workflow", "review_workflow",
        "approve_workflow", "audit_workflow",
    },
    "Consultor": {
        "manage_inventory", "manage_sources", "manage_supply_chain", "manage_automations",
        "manage_integrations", "manage_portfolio", "manage_compliance", "view_compliance",
        "manage_documents", "manage_methodology_governance", "manage_support",
        "manage_commercial", "manage_customer_success", "view_customer_success",
        "manage_impact", "view_impact", "manage_climate_risk", "view_climate_risk",
        "manage_climate_disclosure", "view_climate_disclosure", "manage_consolidation",
        "view_consolidation", "review", "view_methodology",
        "manage_workflow", "execute_workflow", "validate_workflow", "review_workflow",
    },
    "Cliente": {
        "provide_data", "manage_supply_chain", "manage_support", "view_customer_success",
        "view_impact", "view_climate_risk", "view_climate_disclosure", "execute_workflow",
    },
    "Revisor": {
        "review", "approve", "view_methodology", "manage_portfolio", "manage_compliance",
        "view_compliance", "manage_documents", "manage_methodology_governance", "manage_support",
        "view_customer_success", "view_impact", "view_climate_risk",
        "manage_climate_disclosure", "view_climate_disclosure", "view_consolidation",
        "validate_workflow", "review_workflow", "approve_workflow",
    },
    "Verificador": {
        "view_methodology", "external_audit", "manage_portfolio", "view_compliance",
        "view_impact", "view_climate_risk", "view_climate_disclosure", "view_consolidation",
        "audit_workflow",
    },
}

CAPABILITY_LABELS = {
    "manage_org": "Administrar organización",
    "manage_inventory": "Gestionar inventarios",
    "manage_sources": "Gestionar fuentes y datos",
    "provide_data": "Aportar datos y evidencias",
    "review": "Revisar inventarios",
    "approve": "Aprobar y cerrar",
    "external_audit": "Auditoría externa",
    "view_methodology": "Consultar metodología",
    "manage_supply_chain": "Gestionar alcance 3",
    "manage_operations": "Operar plataforma",
    "manage_automations": "Gestionar automatizaciones",
    "manage_integrations": "Gestionar integraciones",
    "manage_portfolio": "Gestionar portafolio",
    "manage_compliance": "Gestionar cumplimiento",
    "view_compliance": "Consultar cumplimiento",
    "manage_documents": "Gestionar documentos",
    "manage_methodology_governance": "Gobernar metodología",
    "manage_readiness": "Gestionar alistamiento",
    "manage_subscription": "Gestionar suscripción",
    "manage_support": "Gestionar soporte",
    "manage_saas": "Administrar SaaS",
    "manage_commercial": "Gestionar operación comercial",
    "manage_customer_success": "Gestionar éxito del cliente",
    "view_customer_success": "Consultar éxito del cliente",
    "manage_impact": "Gestionar inteligencia de impacto",
    "view_impact": "Consultar inteligencia de impacto",
    "manage_climate_risk": "Gestionar riesgos climáticos",
    "view_climate_risk": "Consultar riesgos climáticos",
    "manage_climate_disclosure": "Gestionar divulgación climática",
    "view_climate_disclosure": "Consultar divulgación climática",
    "manage_consolidation": "Gestionar consolidación V1.0",
    "view_consolidation": "Consultar consolidación V1.0",
    "manage_workflow": "Crear, asignar y cancelar trabajo",
    "execute_workflow": "Aceptar y entregar trabajo asignado",
    "validate_workflow": "Validar entregas y controles de calidad",
    "review_workflow": "Revisar y aceptar entregas",
    "approve_workflow": "Cerrar o reabrir trabajo controlado",
    "audit_workflow": "Consultar trazabilidad del trabajo",
}


def capabilities_for(role: str) -> set[str]:
    return set(ROLE_CAPABILITIES.get(role, set()))


def permission_matrix() -> list[dict[str, object]]:
    all_capabilities = sorted(
        {capability for capabilities in ROLE_CAPABILITIES.values() for capability in capabilities},
        key=lambda item: CAPABILITY_LABELS.get(item, item),
    )
    return [
        {
            "capability": capability,
            "label": CAPABILITY_LABELS.get(capability, capability),
            "roles": {role: capability in ROLE_CAPABILITIES.get(role, set()) for role in ROLE_ORDER},
        }
        for capability in all_capabilities
    ]


# Visibility rules mirror route-level authorization. They do not replace backend
# checks; they prevent the interface from offering actions the active role cannot open.
ROUTE_ACCESS_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("/administracion-plataforma", ("manage_operations",)),
    ("/administracion-saas", ("manage_saas",)),
    ("/alistamiento", ("manage_readiness",)),
    ("/automatizaciones", ("manage_automations",)),
    ("/cadena-valor", ("manage_supply_chain", "review", "approve")),
    ("/centro-documental", ("manage_documents",)),
    ("/comercial", ("manage_commercial",)),
    ("/consolidacion", ("view_consolidation", "manage_consolidation")),
    ("/cumplimiento", ("view_compliance", "manage_compliance")),
    ("/direccion-ejecutiva", ("manage_portfolio",)),
    ("/entorno-demo", ("manage_portfolio",)),
    ("/exito-cliente", ("view_customer_success", "manage_customer_success")),
    ("/aseguramiento", ("external_audit", "review", "approve")),
    ("/huella-producto", ("view_methodology", "review", "approve")),
    ("/proyectos-mitigacion", ("view_methodology", "review", "approve")),
    ("/gobierno-metodologico", ("manage_methodology_governance",)),
    ("/integraciones", ("manage_integrations",)),
    ("/inteligencia-producto", ("manage_org", "view_methodology", "manage_portfolio", "view_consolidation")),
    ("/metodologia", ("view_methodology",)),
    ("/operacion-comercial", ("manage_commercial",)),
    ("/operacion-servicio", ("manage_subscription",)),
    ("/operacion", ("manage_operations",)),
    ("/portafolio", ("manage_portfolio",)),
    ("/usuarios", ("manage_org",)),
    ("/verificacion", ("external_audit", "review", "approve")),
)


def can_open_route(user: dict[str, object], route: str | None) -> bool:
    """Return whether a rendered navigation target is meaningful for this role."""
    if not route:
        return False
    path = urlsplit(str(route)).path.rstrip("/") or "/"
    capabilities = set(user.get("capabilities") or set())

    if path.startswith("/inventarios/") and path.endswith("/editar"):
        return "manage_inventory" in capabilities

    if path.startswith("/fuentes/") and "/factores" in path:
        if path.endswith("/revisar"):
            return bool({"review", "approve"} & capabilities)
        return "view_methodology" in capabilities

    for prefix, required in ROUTE_ACCESS_RULES:
        if path == prefix or path.startswith(prefix + "/"):
            return bool(set(required) & capabilities)
    return True
