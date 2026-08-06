from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import Base, EmissionSource, ENGINE, Inventory, SessionLocal, init_db
from app.main import app

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def fresh_database_iteration3():
    # La base semilla aislada se restaura desde tests/conftest.py.
    yield


def login(client: TestClient, email: str = "consultor@calculatuhuella.local") -> None:
    response = client.post("/login", data={"email": email, "password": "Demo2026!"}, follow_redirects=False)
    assert response.status_code == 303


def read(name: str) -> str:
    return (ROOT / "app" / "templates" / name).read_text(encoding="utf-8")


def test_iteration3_information_separates_primary_and_advanced_capture():
    page = read("information.html")
    assert 'class="task-jumpbar"' in page
    assert 'class="form-primary-fields"' in page
    assert 'class="advanced-form-fields"' in page
    assert 'data-exclusive-details="information-create"' in page
    assert "Opciones avanzadas" in page


def test_iteration3_source_page_uses_progressive_methodological_disclosure():
    page = read("source.html")
    assert 'id="datos-actividad"' in page
    assert 'id="factores-predeterminados"' in page
    assert 'id="resultado-gases"' in page
    assert 'id="memoria-calculo"' in page
    assert 'class="candidate-proposal"' in page
    assert 'data-exclusive-details="activity-record-editor"' in page


def test_iteration3_creation_forms_are_not_all_expanded_at_once():
    assert 'class="task-form-disclosure" data-exclusive-details="source-create"' in read("sources.html")
    assert 'class="task-form-disclosure" data-exclusive-details="control-create"' in read("control.html")
    script = (ROOT / "app" / "static" / "js" / "app.js").read_text(encoding="utf-8")
    assert "initializeProgressiveDisclosure" in script
    assert "event.target.closest?.('details')" in script


def test_iteration3_primary_pages_render_with_task_navigation():
    with TestClient(app) as client:
        login(client)
        pages = [
            ("/informacion", "Tareas de información"),
            ("/control", "Tareas de control profesional"),
        ]
        for url, marker in pages:
            response = client.get(url)
            assert response.status_code == 200
            assert marker in response.text

        with SessionLocal() as session:
            inventory_id = session.scalar(select(Inventory.id).order_by(Inventory.id))
            source_id = session.scalar(select(EmissionSource.id).order_by(EmissionSource.id))
        assert inventory_id is not None
        assert source_id is not None

        sources = client.get(f"/inventarios/{inventory_id}/fuentes")
        assert sources.status_code == 200
        assert "Tareas del mapa de fuentes" in sources.text

        source = client.get(f"/fuentes/{source_id}")
        assert source.status_code == 200
        assert "Etapas de revisión de la fuente" in source.text
        assert "Enviar propuesta a revisión" in source.text or "Ya existe una decisión activa" in source.text
