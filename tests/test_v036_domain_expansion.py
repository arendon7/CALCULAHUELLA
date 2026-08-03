from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.architecture import domain_architecture_summary
from app.database import Base, ENGINE, Facility, Inventory, Organization, SessionLocal, init_db
from app.main import app


@pytest.fixture(autouse=True)
def fresh_database_v036():
    Base.metadata.drop_all(ENGINE)
    init_db()
    yield


def login(client: TestClient, email: str = "admin@calculatuhuella.local") -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v036_health_and_expanded_domain_route_parity():
    with TestClient(app) as client:
        assert client.get("/api/health").json()["version"] == "0.45.5"
        login(client)
        summary = client.get("/api/arquitectura/resumen").json()
    assert summary["route_parity_ok"] is True
    assert summary["duplicate_paths"] == []
    assert summary["domain_count"] == 9
    assert summary["owned_route_count"] >= 48
    assert summary["main_lines"] < 4700


def test_v036_routes_are_owned_by_new_domain_modules():
    project_dir = Path(__file__).resolve().parents[1]
    summary = domain_architecture_summary(app, project_dir)
    actual = {item["code"]: item["route_count"] for item in summary["domains"]}
    assert actual == {
        "demo_environment": 4,
        "organizations": 4,
        "information": 10,
        "review": 10,
        "users": 4,
        "inventories": 13,
        "reports": 4,
        "operations": 14,
        "product_intelligence": 8,
    }
    main_source = (project_dir / "app" / "main.py").read_text(encoding="utf-8")
    for decorator in (
        '@app.get("/organizacion"',
        '@app.get("/informacion"',
        '@app.get("/control"',
        '@app.post("/sedes/nueva"',
        '@app.post("/informacion/datos/nuevo"',
        '@app.post("/control/inventario/aprobar"',
    ):
        assert decorator not in main_source
    assert "register_organization_routes(" in main_source
    assert "register_information_routes(" in main_source
    assert "register_review_routes(" in main_source


def test_v036_organization_information_and_review_pages_load():
    with TestClient(app) as client:
        login(client)
        for path in ("/organizacion", "/informacion", "/informacion/importar", "/control", "/consolidacion"):
            response = client.get(path)
            assert response.status_code == 200, path
            assert "Calcula tu Huella" in response.text


def test_v036_organization_and_facility_changes_persist():
    with TestClient(app) as client:
        login(client)
        response = client.post(
            "/organizacion/editar",
            data={
                "name": "Industrias Andinas Modular S.A.S.",
                "trade_name": "Andinas Modular",
                "tax_id": "901.555.101-8",
                "sector": "Manufactura",
                "ciiu_code": "C2029",
                "country": "Colombia",
                "department": "Antioquia",
                "city": "Medellín",
                "employees": "190",
                "contact_name": "Ana Martínez",
                "contact_email": "ambiental@andinas.demo",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        response = client.post(
            "/sedes/nueva",
            data={
                "name": "Centro modular",
                "facility_type": "Administrativa",
                "city": "Medellín",
                "address": "Calle 1",
                "employees": "12",
                "ownership_percentage": "100",
                "operational_control": "on",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
    with SessionLocal() as session:
        org = session.scalar(select(Organization).where(Organization.trade_name == "Andinas Modular"))
        facility = session.scalar(select(Facility).where(Facility.name == "Centro modular"))
        assert org is not None and org.employees == 190
        assert facility is not None and facility.organization_id == org.id
        assert facility.operational_control is True


def test_v036_existing_inventory_is_upgraded_without_recalculation():
    with SessionLocal() as session:
        inventory = session.scalar(select(Inventory).order_by(Inventory.id))
        assert inventory is not None
        assert inventory.version == "0.45"
