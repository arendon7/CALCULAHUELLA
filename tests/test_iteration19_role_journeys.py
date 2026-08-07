from __future__ import annotations

import pytest

from app.access_control import ROLE_CAPABILITIES, can_open_route
from app.main import app  # noqa: F401 - importing the app installs Mi trabajo navigation
from app.product_experience import navigation_for

pytestmark = pytest.mark.smoke


EXPECTED_ESSENTIAL_NAVIGATION = {
    "Administrador": [
        "Mi trabajo",
        "Portafolio de empresas",
        "Continuar recorrido",
        "Datos y avance",
        "Calidad y riesgos",
        "Resultados",
        "Cierre e informes",
        "Plan de reducción",
    ],
    "Consultor": [
        "Mi trabajo",
        "Continuar recorrido",
        "Fuentes y límites",
        "Datos y evidencias",
        "Calidad y revisión",
        "Resultados",
        "Cierre e informes",
        "Plan de reducción",
    ],
    "Cliente": [
        "Mi trabajo",
        "Continuar mi recorrido",
        "Cargar datos",
        "Datos y soportes",
        "Revisar calidad",
        "Ver resultados",
    ],
    "Revisor": [
        "Mi trabajo",
        "Prioridades de revisión",
        "Calidad de datos",
        "Revisión técnica",
        "Resultados calculados",
        "Cierre metodológico",
        "Expediente de cierre",
    ],
    "Verificador": [
        "Mi trabajo",
        "Plan de verificación",
        "Paquete verificable",
        "Metodología y límites",
        "Reproducir resultados",
        "Hallazgos",
        "Aseguramiento",
    ],
}


ROUTE_EXPECTATIONS = {
    "/usuarios": {"Administrador"},
    "/operacion": {"Administrador"},
    "/portafolio": {"Administrador", "Consultor", "Revisor", "Verificador"},
    "/metodologia/nucleo": {"Administrador", "Consultor", "Revisor", "Verificador"},
    "/aseguramiento": {"Administrador", "Consultor", "Revisor", "Verificador"},
}


def _user(role: str) -> dict[str, object]:
    return {"role": role, "capabilities": ROLE_CAPABILITIES[role]}


@pytest.mark.parametrize("role", list(EXPECTED_ESSENTIAL_NAVIGATION))
def test_iteration19_every_role_has_exact_essential_journey(role: str) -> None:
    navigation = navigation_for(_user(role), "essential")
    labels = [item["label"] for section in navigation["core"] for item in section["items"]]
    assert labels == EXPECTED_ESSENTIAL_NAVIGATION[role]
    assert labels[0] == "Mi trabajo"
    assert "Centro de trabajo" not in labels


@pytest.mark.parametrize("route,allowed_roles", ROUTE_EXPECTATIONS.items())
def test_iteration19_navigation_never_offers_sensitive_route_to_wrong_role(
    route: str,
    allowed_roles: set[str],
) -> None:
    for role in ROLE_CAPABILITIES:
        assert can_open_route(_user(role), route) is (role in allowed_roles)


def test_iteration19_work_queue_scope_and_creation_follow_capabilities() -> None:
    for role, capabilities in ROLE_CAPABILITIES.items():
        can_create = "manage_workflow" in capabilities
        can_view_all = bool(
            capabilities
            & {
                "manage_workflow",
                "validate_workflow",
                "review_workflow",
                "approve_workflow",
                "audit_workflow",
            }
        )
        assert can_create is (role in {"Administrador", "Consultor"})
        assert can_view_all is (role != "Cliente")


def test_iteration19_role_separation_preserves_workflow_duties() -> None:
    assert "execute_workflow" in ROLE_CAPABILITIES["Cliente"]
    assert "manage_workflow" not in ROLE_CAPABILITIES["Cliente"]
    assert "review_workflow" not in ROLE_CAPABILITIES["Cliente"]
    assert "approve_workflow" not in ROLE_CAPABILITIES["Cliente"]

    assert "manage_workflow" in ROLE_CAPABILITIES["Consultor"]
    assert "approve_workflow" not in ROLE_CAPABILITIES["Consultor"]

    assert {"validate_workflow", "review_workflow", "approve_workflow"} <= ROLE_CAPABILITIES["Revisor"]
    assert "manage_workflow" not in ROLE_CAPABILITIES["Revisor"]

    assert "audit_workflow" in ROLE_CAPABILITIES["Verificador"]
    assert "manage_workflow" not in ROLE_CAPABILITIES["Verificador"]
    assert "approve_workflow" not in ROLE_CAPABILITIES["Verificador"]

    assert {"manage_workflow", "approve_workflow", "audit_workflow"} <= ROLE_CAPABILITIES["Administrador"]
