from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import Base, ENGINE, EmissionSource, Inventory, SessionLocal, init_db
from app.inventory_starters import starter_pack_catalog
from app.main import app

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def fresh_database():
    # La base semilla aislada se restaura desde tests/conftest.py.
    yield


def login(client: TestClient, email: str = "admin@calculatuhuella.local") -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def inventory_payload(**overrides: str) -> dict[str, str]:
    payload = {
        "name": "Inventario guiado 2026",
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "objective": "Crear una línea base verificable",
        "base_year": "2026",
        "methodology": "GHG Protocol + ISO 14064-1",
        "methodology_version": "GHG Protocol Corporate Standard · ISO 14064-1:2018",
        "gwp_version": "IPCC AR6 · 100 años",
        "consolidation_approach": "Control operacional",
        "materiality_threshold": "5",
        "notes": "Prueba del primer inventario",
        "starter_pack": "productive",
        "source_responsible": "Coordinación ambiental",
    }
    payload.update(overrides)
    return payload


def test_starter_catalog_has_controlled_sector_packs():
    catalog = starter_pack_catalog()
    assert [item["code"] for item in catalog] == ["services", "productive", "agro", "waste"]
    assert all(item["source_count"] >= 5 for item in catalog)
    waste = next(item for item in catalog if item["code"] == "waste")
    assert any(source["name"] == "Tratamiento biológico de residuos" for source in waste["sources"])
    assert any(source["preferred_unit"] == "t·km" for source in waste["sources"])


def test_inventory_creation_is_a_four_step_guided_wizard():
    with TestClient(app) as client:
        login(client)
        response = client.get("/inventarios/nuevo")
        assert response.status_code == 200
        assert response.text.count("data-inventory-step") == 4
        assert "Servicios y oficinas" in response.text
        assert "Operación productiva" in response.text
        assert "Gestión de residuos" in response.text
        assert str(date.today().year) in response.text
    javascript = (ROOT / "app" / "static" / "js" / "app.js").read_text(encoding="utf-8")
    assert "initializeInventoryWizard" in javascript
    assert "initializeActivityUnitSuggestion" in javascript


def test_inventory_pack_creates_editable_sources_and_redirects_to_map():
    with TestClient(app) as client:
        login(client)
        response = client.post("/inventarios/nuevo", data=inventory_payload(), follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"].endswith("/fuentes")
    with SessionLocal() as session:
        inventory = session.scalar(select(Inventory).where(Inventory.name == "Inventario guiado 2026"))
        assert inventory is not None
        sources = list(session.scalars(select(EmissionSource).where(EmissionSource.inventory_id == inventory.id)))
        assert len(sources) == 8
        electricity = next(source for source in sources if source.name == "Electricidad comprada")
        assert electricity.scope == 2
        assert electricity.preferred_unit == "kWh"
        assert electricity.responsible == "Coordinación ambiental"
        assert inventory.current_stage == "Fuentes"
        assert inventory.progress >= 28


def test_applying_same_pack_twice_does_not_duplicate_sources():
    with TestClient(app) as client:
        login(client)
        client.post("/inventarios/nuevo", data=inventory_payload())
    with SessionLocal() as session:
        inventory = session.scalar(select(Inventory).where(Inventory.name == "Inventario guiado 2026"))
        inventory_id = inventory.id
    with TestClient(app) as client:
        login(client)
        first = client.post(
            f"/inventarios/{inventory_id}/fuentes/paquete",
            data={"pack_code": "productive", "responsible": "Coordinación ambiental"},
            follow_redirects=False,
        )
        second = client.post(
            f"/inventarios/{inventory_id}/fuentes/paquete",
            data={"pack_code": "productive", "responsible": "Coordinación ambiental"},
            follow_redirects=False,
        )
        assert first.status_code == 303
        assert second.status_code == 303
    with SessionLocal() as session:
        count = len(list(session.scalars(select(EmissionSource).where(EmissionSource.inventory_id == inventory_id))))
        assert count == 8


def test_source_configuration_and_first_data_guidance_are_operational():
    with SessionLocal() as session:
        source = session.scalar(select(EmissionSource).order_by(EmissionSource.id))
        source_id = source.id
    with TestClient(app) as client:
        login(client)
        response = client.post(
            f"/fuentes/{source_id}/configurar",
            data={
                "name": "Electricidad de red",
                "scope": "2",
                "category": "Electricidad adquirida",
                "responsible": "Gestión ambiental",
                "materiality": "Alta",
                "data_frequency": "Mensual",
                "preferred_unit": "kWh",
                "included": "on",
                "exclusion_reason": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        information = client.get("/informacion")
        assert information.status_code == 200
        assert "data-activity-form" in information.text
        assert "data-preferred-unit=\"kWh\"" in information.text
        template = (ROOT / "app" / "templates" / "information.html").read_text(encoding="utf-8")
        assert "Empieza con un dato fácil de comprobar" in template
    with SessionLocal() as session:
        source = session.get(EmissionSource, source_id)
        assert source.name == "Electricidad de red"
        assert source.responsible == "Gestión ambiental"
        assert source.included is True
