from __future__ import annotations

from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.database import ActivityData, Base, ENGINE, SessionLocal, init_db
from app.main import app

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture(autouse=True)
def fresh_database():
    # La base semilla aislada se restaura desde tests/conftest.py.
    yield

def login(client: TestClient, email: str = "consultor@calculatuhuella.local") -> None:
    response = client.post("/login", data={"email": email, "password": "Demo2026!"}, follow_redirects=False)
    assert response.status_code == 303

def test_v051_public_content_is_clear_and_methodologically_bounded():
    with TestClient(app) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert "Mide lo que corresponde" in page.text
        assert "Software y acompañamiento proporcionales" in page.text
        assert "Preguntas que conviene resolver" in page.text
        assert "Las emisiones evitadas" in page.text
        assert "EL FLUJO QUE PROPONE" not in page.text

def test_v051_work_center_prioritizes_next_action_and_separates_controls():
    with TestClient(app) as client:
        login(client)
        page = client.get("/dashboard")
        assert page.status_code == 200
        assert "TU SIGUIENTE ACCIÓN" in page.text
        assert "CONFIANZA" in page.text
        assert "CONTROL METODOLÓGICO" in page.text
        assert "Separación obligatoria" in page.text

def test_v051_guide_explains_process_states_limits_and_glossary():
    with TestClient(app) as client:
        login(client, "cliente@calculatuhuella.local")
        page = client.get("/guia")
        assert page.status_code == 200
        assert "Seis preguntas que ordenan el inventario" in page.text
        assert "QUÉ HACE Y QUÉ NO HACE" in page.text
        assert "Dato de actividad" in page.text
        assert "Emisión evitada" in page.text
        assert "Compensación" in page.text

def test_v051_factor_page_displays_six_environmental_controls():
    with TestClient(app) as client:
        login(client)
        page = client.get("/fuentes/1")
        assert page.status_code == 200
        assert "Seis preguntas de control metodológico" in page.text
        assert "¿Puede existir doble conteo?" in page.text
        assert "un puntaje de compatibilidad" in page.text

def test_v051_source_page_focuses_factor_review_on_selected_record():
    with SessionLocal() as session:
        record = session.scalar(select(ActivityData).where(ActivityData.source_id == 1).order_by(ActivityData.id))
        assert record is not None
        record_id = record.id
    with TestClient(app) as client:
        login(client)
        default_page = client.get("/fuentes/1")
        assert default_page.status_code == 200
        assert "Analiza un dato a la vez" in default_page.text
        assert "La vista inicial muestra el registro más reciente" in default_page.text
        focused = client.get(f"/fuentes/1?activity_data_id={record_id}")
        assert focused.status_code == 200
        assert "La vista está enfocada en el dato seleccionado" in focused.text
        assert f'value="{record_id}" selected' in focused.text

def test_v051_visible_labels_avoid_stale_versions_and_overclaiming():
    analysis = (ROOT / "app/templates/analysis.html").read_text(encoding="utf-8")
    users = (ROOT / "app/templates/users.html").read_text(encoding="utf-8")
    methodology = (ROOT / "app/templates/methodology_core.html").read_text(encoding="utf-8")
    demo = (ROOT / "app/templates/demo_environment.html").read_text(encoding="utf-8")
    assert "Funcional · V0.6" not in analysis
    assert "Funcional · V0.27" not in users
    assert "La V0.28 amplía" not in methodology
    assert "Validar integridad demo" in demo
    assert "Entorno demo certificado" not in demo

def test_v051_release_and_documentation_are_aligned():
    assert 'version: str = "1.0.0"' in (ROOT / "app/config.py").read_text(encoding="utf-8")
    assert 'ENGINE_VERSION = "1.1.0"' in (ROOT / "app/calculations.py").read_text(encoding="utf-8")
    assert (ROOT / "V051_AUDITORIA_EXPERIENCIA_CONTENIDO_AMBIENTAL.md").is_file()
    assert (ROOT / "GUIA_DE_CONTENIDO_Y_UX_V051.md").is_file()
    assert (ROOT / "app/templates/guide.html").is_file()
