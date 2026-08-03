from __future__ import annotations

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
    },
    "Consultor": {
        "manage_inventory", "manage_sources", "manage_supply_chain", "manage_automations",
        "manage_integrations", "manage_portfolio", "manage_compliance", "view_compliance",
        "manage_documents", "manage_methodology_governance", "manage_support",
        "manage_commercial", "manage_customer_success", "view_customer_success",
        "manage_impact", "view_impact", "manage_climate_risk", "view_climate_risk",
        "manage_climate_disclosure", "view_climate_disclosure", "manage_consolidation",
        "view_consolidation", "review", "view_methodology",
    },
    "Cliente": {
        "provide_data", "manage_supply_chain", "manage_support", "view_customer_success",
        "view_impact", "view_climate_risk", "view_climate_disclosure",
    },
    "Revisor": {
        "review", "approve", "view_methodology", "manage_portfolio", "manage_compliance",
        "view_compliance", "manage_documents", "manage_methodology_governance", "manage_support",
        "view_customer_success", "view_impact", "view_climate_risk",
        "manage_climate_disclosure", "view_climate_disclosure", "view_consolidation",
    },
    "Verificador": {
        "view_methodology", "external_audit", "manage_portfolio", "view_compliance",
        "view_impact", "view_climate_risk", "view_climate_disclosure", "view_consolidation",
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
