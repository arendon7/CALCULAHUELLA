from __future__ import annotations

from pathlib import Path

from app.main import app

ROOT = Path(__file__).resolve().parents[1]

NOTIFICATION_ROUTES = {
    ("GET", "/notificaciones"),
    ("POST", "/notificaciones/{notification_id}/leer"),
    ("POST", "/notificaciones/leer-todas"),
    ("POST", "/notificaciones/preferencias"),
}


def test_v190_notifications_have_dedicated_http_authority():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    module_source = (ROOT / "app/notifications_web.py").read_text(encoding="utf-8")
    assert '@app.get("/notificaciones"' not in main_source
    assert '@app.post("/notificaciones/' not in main_source
    assert "register_notification_routes(" in main_source
    assert module_source.count("@app.") == 4
    assert "Notification.organization_id" in module_source
    assert "Notification.user_id" in module_source
    assert "get_or_create_preference" in module_source
    assert '@app.get("/portafolio"' not in module_source


def test_v190_notification_route_contract_is_unique_and_complete():
    actual = []
    relevant = {path for _, path in NOTIFICATION_ROUTES}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if path in relevant:
            actual.extend((method, path) for method in methods if method in {"GET", "POST"})
    assert set(actual) == NOTIFICATION_ROUTES
    assert len(actual) == len(NOTIFICATION_ROUTES)
