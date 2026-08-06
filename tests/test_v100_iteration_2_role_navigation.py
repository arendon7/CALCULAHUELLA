from pathlib import Path

from app.access_control import ROLE_CAPABILITIES, can_open_route
from app.product_experience import navigation_for


def user_for(role: str) -> dict[str, object]:
    return {"role": role, "capabilities": ROLE_CAPABILITIES[role]}


def test_sensitive_routes_are_hidden_from_client() -> None:
    client = user_for("Cliente")
    forbidden = [
        "/usuarios",
        "/metodologia",
        "/metodologia/biblioteca-factores/1",
        "/operacion-servicio",
        "/consolidacion",
        "/inventarios/1/editar",
        "/inteligencia-producto",
    ]
    assert all(not can_open_route(client, route) for route in forbidden)
    assert can_open_route(client, "/dashboard")
    assert can_open_route(client, "/informacion")
    assert can_open_route(client, "/cadena-valor")


def test_role_specific_routes_remain_available() -> None:
    assert can_open_route(user_for("Consultor"), "/metodologia/biblioteca-factores")
    assert can_open_route(user_for("Consultor"), "/inventarios/1/editar")
    assert can_open_route(user_for("Revisor"), "/verificacion")
    assert not can_open_route(user_for("Revisor"), "/inventarios/1/editar")
    assert can_open_route(user_for("Verificador"), "/verificacion")
    assert can_open_route(user_for("Administrador"), "/operacion-servicio")


def test_service_operations_navigation_is_capability_gated() -> None:
    client_navigation = navigation_for(user_for("Cliente"), "complete")
    admin_navigation = navigation_for(user_for("Administrador"), "complete")
    client_links = {
        item["href"]
        for group_name in ("core", "advanced", "internal")
        for section in client_navigation[group_name]
        for item in section["items"]
    }
    admin_links = {
        item["href"]
        for group_name in ("core", "advanced", "internal")
        for section in admin_navigation[group_name]
        for item in section["items"]
    }
    assert "/operacion-servicio" not in client_links
    assert "/operacion-servicio" in admin_links


def test_permission_sensitive_templates_use_route_policy() -> None:
    templates = Path(__file__).parents[1] / "app" / "templates"
    for filename in (
        "modules.html",
        "consolidation.html",
        "guide.html",
        "organization.html",
        "onboarding.html",
        "guided_onboarding.html",
        "dashboard.html",
        "delivery.html",
    ):
        assert "can_open_route" in (templates / filename).read_text(encoding="utf-8")


def test_factor_controls_and_pilot_template_are_state_gated() -> None:
    templates = Path(__file__).parents[1] / "app" / "templates"
    source = (templates / "source.html").read_text(encoding="utf-8")
    quality = (templates / "data_quality.html").read_text(encoding="utf-8")
    assert "selected_activity_data_id and user.can_view_methodology" in source
    assert "La selección metodológica corresponde al consultor o revisor" in source
    assert "{% if summary.execution %}" in quality
    assert "Plantilla pendiente de piloto" in quality
