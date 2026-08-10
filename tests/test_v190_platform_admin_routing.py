from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]

PLATFORM_ADMIN_ROUTES = {
    ("GET", "/administracion-plataforma"),
    ("POST", "/administracion-plataforma/configuracion"),
    ("POST", "/administracion-plataforma/notificaciones/prueba"),
    ("POST", "/administracion-plataforma/notificaciones/procesar"),
}


def _login(client: TestClient, email: str) -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v190_platform_admin_has_dedicated_http_authority():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    module_source = (ROOT / "app/platform_admin_web.py").read_text(encoding="utf-8")
    assert '@app.get("/administracion-plataforma"' not in main_source
    assert '@app.post("/administracion-plataforma/' not in main_source
    assert "register_platform_admin_routes(" in main_source
    assert module_source.count("@app.") == 4
    assert "PlatformSetting" in module_source
    assert "notify_roles" in module_source
    assert "process_pending_notifications" in module_source
    assert "storage.diagnostics" in module_source
    assert '@app.get("/portafolio"' not in module_source


def test_v190_platform_admin_route_contract_is_unique_and_complete():
    actual = []
    relevant = {path for _, path in PLATFORM_ADMIN_ROUTES}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if path in relevant:
            actual.extend((method, path) for method in methods if method in {"GET", "POST"})
    assert set(actual) == PLATFORM_ADMIN_ROUTES
    assert len(actual) == len(PLATFORM_ADMIN_ROUTES)


def test_v190_platform_admin_remains_restricted():
    with TestClient(app) as client:
        _login(client, "consultor@calculatuhuella.local")
        assert client.get("/administracion-plataforma").status_code == 403
        client.post("/logout")
        _login(client, "admin@calculatuhuella.local")
        assert client.get("/administracion-plataforma").status_code == 200
