from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import Base, ENGINE, Inventory, LandCarbonEntry, SessionLocal, init_db
from app.land_removals import land_summary, validate_entry
from app.main import app


@pytest.fixture(autouse=True)
def fresh_database_iteration7():
    # La base semilla aislada se restaura desde tests/conftest.py.
    yield


def login(client: TestClient, email: str = "admin@calculatuhuella.local") -> None:
    response = client.post("/login", data={"email": email, "password": "Demo2026!"}, follow_redirects=False)
    assert response.status_code == 303


def test_removal_requires_storage_monitoring_and_lifecycle():
    payload = {
        "entry_type": "Remoción de CO2",
        "quantity_tco2e": 12.5,
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 12, 31),
        "methodology": "GHG Protocol LSR",
        "source_reference": "Estudio de campo",
        "uncertainty_percentage": 20,
        "storage_duration_years": 0,
        "reversal_monitoring": False,
        "lifecycle_complete": False,
        "reporting_scope": "Fuera de alcances",
        "gas": "CO2",
    }
    errors = validate_entry(payload)
    assert len(errors) == 3
    assert any("duración" in item for item in errors)
    assert any("reversión" in item for item in errors)
    assert any("ciclo de vida" in item for item in errors)


def test_avoided_emissions_cannot_be_inside_scopes():
    errors = validate_entry({
        "entry_type": "Emisión evitada / beneficio circular", "quantity_tco2e": 10,
        "start_date": date(2026, 1, 1), "end_date": date(2026, 12, 31),
        "methodology": "Escenario comparativo", "source_reference": "Memoria técnica",
        "uncertainty_percentage": 10, "storage_duration_years": 0,
        "reporting_scope": "Alcance 1", "gas": "CO2",
    })
    assert any("fuera de los alcances" in item for item in errors)


def test_page_api_and_create_valid_removal():
    with TestClient(app) as client:
        login(client)
        page = client.get("/metodologia/tierras-remociones")
        assert page.status_code == 200
        assert "Tierras, remociones y carbono biogénico" in page.text
        response = client.post("/metodologia/tierras-remociones/nueva", data={
            "entry_type": "Remoción de CO2", "activity_name": "Carbono orgánico del suelo piloto",
            "land_category": "Tierras agrícolas", "carbon_pool": "Carbono orgánico del suelo",
            "location": "Támesis", "reporting_scope": "Fuera de alcances", "gas": "CO2",
            "quantity_tco2e": "18.4", "start_date": "2026-01-01", "end_date": "2026-12-31",
            "methodology": "GHG Protocol LSR Standard v1.0", "source_reference": "Muestreo de suelo lote A",
            "traceability_level": "Predio específico", "uncertainty_percentage": "18",
            "storage_duration_years": "20", "reversal_monitoring": "on", "lifecycle_complete": "on",
            "verified": "on", "notes": "Piloto metodológico; no reduce automáticamente el inventario.",
        }, follow_redirects=False)
        assert response.status_code == 303
        api = client.get("/api/metodologia/tierras-remociones")
        assert api.status_code == 200
        assert api.json()["summary"]["removals"] == 18.4
    with SessionLocal() as session:
        item = session.scalar(select(LandCarbonEntry).where(LandCarbonEntry.activity_name.like("Carbono%")))
        assert item is not None
        assert item.reversal_monitoring is True
        assert item.lifecycle_complete is True


def test_summary_never_nets_separate_categories():
    class Item:
        def __init__(self, entry_type, quantity, **kwargs):
            self.entry_type = entry_type; self.quantity_tco2e = quantity
            self.land_category = kwargs.get("land_category", "Tierras agrícolas")
            self.status = kwargs.get("status", "Borrador")
            self.verified = kwargs.get("verified", False)
            self.activity_name = kwargs.get("activity_name", entry_type)
            self.traceability_level = kwargs.get("traceability_level", "Predio específico")
            self.uncertainty_percentage = kwargs.get("uncertainty_percentage", 0)
    summary = land_summary([
        Item("Emisión de manejo de tierras", 100), Item("Remoción de CO2", 30),
        Item("Carbono almacenado en producto", 20), Item("Emisión evitada / beneficio circular", 40),
    ])
    assert summary["gross_land_emissions"] == 100
    assert summary["removals"] == 30
    assert summary["product_storage"] == 20
    assert summary["avoided"] == 40
    assert "net" not in summary
