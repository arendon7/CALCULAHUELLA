from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.calculations import source_calculation_summary
from app.db.base import SessionLocal
from app.db.models import EmissionSource, Inventory
from app.main import app

ROOT = Path(__file__).resolve().parents[1]

CALCULATION_ROUTES = {
    ("GET", "/calculos"),
    ("GET", "/inventarios/{inventory_id}/calculos"),
    ("POST", "/inventarios/{inventory_id}/recalcular"),
}


def _login(client: TestClient) -> None:
    response = client.post(
        "/login",
        data={"email": "consultor@calculatuhuella.local", "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v160_calculation_routes_have_dedicated_http_authority():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    module_source = (ROOT / "app/calculation_web.py").read_text(encoding="utf-8")
    assert '@app.get("/calculos"' not in main_source
    assert '@app.post("/inventarios/{inventory_id}/recalcular"' not in main_source
    assert "register_calculation_routes(" in main_source
    assert module_source.count("@app.") == 3
    assert '@app.get("/inventarios/{inventory_id}/calculos"' in module_source
    assert "recalculate_inventory" in module_source
    assert "source_calculation_summary" in module_source
    assert "def recalculate_inventory(" not in module_source
    assert "def source_calculation_summary(" not in module_source


def test_v160_calculation_route_contract_is_unique_and_complete():
    actual = []
    relevant = {path for _, path in CALCULATION_ROUTES}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if path in relevant:
            actual.extend((method, path) for method in methods if method in {"GET", "POST"})
    assert set(actual) == CALCULATION_ROUTES
    assert len(actual) == len(CALCULATION_ROUTES)


def test_v160_calculation_page_uses_existing_engine_results():
    with SessionLocal() as session:
        inventory = session.scalar(select(Inventory).order_by(Inventory.id))
        source = session.scalar(select(EmissionSource).where(EmissionSource.inventory_id == inventory.id).order_by(EmissionSource.id))
        assert inventory is not None and source is not None
        before = source_calculation_summary(session, source.id)
        source_id = source.id
    with TestClient(app) as client:
        _login(client)
        page = client.get("/calculos")
        assert page.status_code == 200
        response = client.post(
            f"/inventarios/{inventory.id}/recalcular",
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/calculos"
    with SessionLocal() as session:
        after = source_calculation_summary(session, source_id)
        assert len(after["calculations"]) == len(before["calculations"])
        assert after["errors"] == before["errors"]
