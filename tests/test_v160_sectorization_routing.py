from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.base import SessionLocal
from app.db.models import EmissionSource, SectorTemplate
from app.main import app

ROOT = Path(__file__).resolve().parents[1]

SECTORIZATION_ROUTES = {
    ("GET", "/sectorizacion"),
    ("POST", "/sectorizacion/aplicar"),
}


def _login(client: TestClient) -> None:
    response = client.post(
        "/login",
        data={"email": "consultor@calculatuhuella.local", "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v160_sectorization_has_dedicated_http_authority():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    module_source = (ROOT / "app/sectorization_web.py").read_text(encoding="utf-8")
    assert '@app.get("/sectorizacion"' not in main_source
    assert '@app.post("/sectorizacion/aplicar"' not in main_source
    assert "register_sectorization_routes(" in main_source
    assert module_source.count("@app.") == 2
    assert "refresh_progress" in module_source
    assert "SourceFactorAssignment" in module_source


def test_v160_sectorization_route_contract_is_unique_and_complete():
    actual = []
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if path and path.startswith("/sectorizacion"):
            actual.extend((method, path) for method in methods if method in {"GET", "POST"})
    assert set(actual) == SECTORIZATION_ROUTES
    assert len(actual) == len(SECTORIZATION_ROUTES)


def test_v160_sector_template_application_remains_idempotent():
    with TestClient(app) as client:
        _login(client)
        page = client.get("/sectorizacion")
        assert page.status_code == 200
        with SessionLocal() as session:
            template = session.scalar(
                select(SectorTemplate).where(SectorTemplate.sector == "Servicios y oficinas")
            )
            assert template is not None
            before = session.scalar(
                select(func.count()).select_from(EmissionSource).where(EmissionSource.inventory_id == 1)
            ) or 0
            template_id = template.id
        first = client.post(
            "/sectorizacion/aplicar",
            data={
                "inventory_id": 1,
                "template_id": template_id,
                "facility_id": 1,
                "include_optional": "true",
            },
            follow_redirects=False,
        )
        assert first.status_code == 303
        with SessionLocal() as session:
            after = session.scalar(
                select(func.count()).select_from(EmissionSource).where(EmissionSource.inventory_id == 1)
            ) or 0
        assert after > before
        second = client.post(
            "/sectorizacion/aplicar",
            data={
                "inventory_id": 1,
                "template_id": template_id,
                "facility_id": 1,
                "include_optional": "true",
            },
            follow_redirects=False,
        )
        assert second.status_code == 303
        with SessionLocal() as session:
            final_count = session.scalar(
                select(func.count()).select_from(EmissionSource).where(EmissionSource.inventory_id == 1)
            ) or 0
        assert final_count == after
