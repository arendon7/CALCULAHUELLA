from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.data_request_status import is_data_request_open
from app.main import app

ROOT = Path(__file__).resolve().parents[1]
APP_CSS = ROOT / "app" / "static" / "css" / "app.css"
DATA_CSS = ROOT / "app" / "static" / "css" / "v2.1-data-workflows.css"
BROWSER_GATE = ROOT / "scripts" / "browser_workflow_gate.py"
INFORMATION = ROOT / "app" / "templates" / "information.html"
SOURCES = ROOT / "app" / "templates" / "sources.html"
SOURCE = ROOT / "app" / "templates" / "source.html"


def _login(client: TestClient, email: str) -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


@pytest.mark.smoke
def test_v213_data_workflow_layer_loads_after_core_workflows() -> None:
    css = APP_CSS.read_text(encoding="utf-8")
    assert 'url("./v2.1-core-workflows.css")' in css
    assert 'url("./v2.1-data-workflows.css")' in css
    assert css.index('url("./v2.1-core-workflows.css")') < css.index('url("./v2.1-data-workflows.css")')


@pytest.mark.smoke
def test_information_keeps_task_first_navigation_and_guided_capture_entry() -> None:
    template = INFORMATION.read_text(encoding="utf-8")
    css = DATA_CSS.read_text(encoding="utf-8")
    assert 'class="work-command information-command"' in template
    assert 'data-default-task="{{ information_focus.task }}"' in template
    assert 'href="/captura-guiada"' in template
    assert "{{ open_requests|length }}" in template
    for target in ('data-task-target="datos"', 'data-task-target="solicitudes"', 'data-task-target="evidencias"'):
        assert target in template
    assert ".task-jumpbar{position:sticky" in css
    assert ".request-list>article{position:relative;display:grid" in css
    assert ".information-layout>.sticky-form{position:sticky" in css


@pytest.mark.smoke
def test_data_request_status_semantics_cover_current_and_legacy_closed_values() -> None:
    for status in ("Completado", "Completada", "Cerrado", "Cerrada"):
        assert is_data_request_open(status) is False
    for status in ("Pendiente", "En preparación", "Cargado", "En revisión", "Devuelto"):
        assert is_data_request_open(status) is True


@pytest.mark.smoke
def test_client_information_opens_requests_when_work_is_pending() -> None:
    with TestClient(app) as client:
        _login(client, "cliente@calculatuhuella.local")
        page = client.get("/informacion")
        assert page.status_code == 200
        assert 'data-default-task="solicitudes"' in page.text
        assert "RESPONDE LO PENDIENTE" in page.text
        assert "Abrir solicitudes" in page.text


@pytest.mark.smoke
def test_reviewer_information_prioritizes_evidence_review() -> None:
    with TestClient(app) as client:
        _login(client, "revisor@calculatuhuella.local")
        page = client.get("/informacion")
        assert page.status_code == 200
        assert 'data-default-task="evidencias"' in page.text
        assert "REVISA LA EVIDENCIA" in page.text
        assert "Revisar evidencias" in page.text


@pytest.mark.smoke
def test_source_map_keeps_assisted_setup_materiality_and_next_step_visible() -> None:
    template = SOURCES.read_text(encoding="utf-8")
    css = DATA_CSS.read_text(encoding="utf-8")
    assert 'class="first-inventory-route card"' in template
    assert 'id="mapa-fuentes"' in template
    assert 'class="card source-next-step"' in template
    assert ".first-inventory-route{display:grid" in css
    assert ".source-summary-grid .mini-card:nth-child(3)" in css
    assert "#mapa-fuentes table{min-width:1120px}" in css
    assert ".source-next-step{display:grid" in css


@pytest.mark.smoke
def test_source_detail_orients_next_task_from_real_source_state() -> None:
    template = SOURCE.read_text(encoding="utf-8")
    css = DATA_CSS.read_text(encoding="utf-8")
    assert "namespace(pending=0, applied_records=0, missing_records=0)" in template
    assert "['Propuesto','Requiere ajuste']" in template
    assert "['Aprobado','Seleccionado']" in template
    assert 'data-source-focus="{{ focus.task }}"' in template
    assert 'data-default-task="{{ focus.task }}"' in template
    assert "CORREGIR CÁLCULO" in template
    assert "DECISIÓN METODOLÓGICA" in template
    assert "VALIDAR ALERTAS" in template
    assert "RESULTADO TRAZABLE" in template
    assert "Cadena de trazabilidad" in template
    assert "Trazabilidad completa" not in template
    assert 'data-default-task="datos"' not in template
    assert 'class="calculation-notice notice-success"' not in template
    assert 'id="datos-actividad"' in template
    assert 'id="conversacion-tecnica"' in template
    assert ".source-config-panel" in css
    assert ".source-detail-taskbar" in css
    assert "#datos-actividad table{min-width:980px}" in css
    assert "env(safe-area-inset-bottom)" in css


@pytest.mark.smoke
def test_data_workflows_collapse_deliberately_on_mobile_without_masking_overflow() -> None:
    css = DATA_CSS.read_text(encoding="utf-8")
    assert "@media(max-width:900px)" in css
    assert "@media(max-width:620px)" in css
    assert ".information-layout,body.app-shell .information-layout.wide-form-layout,body.app-shell .source-management-layout{grid-template-columns:1fr;width:100%;min-width:0;max-width:100%}" in css
    assert ".information-layout>*{width:100%;min-width:0;max-width:100%}" in css
    assert ".information-layout .responsive-table{width:100%;min-width:0;max-width:100%}" in css
    assert ".task-jumpbar{top:58px" in css
    assert "overflow-x:hidden" not in css
    assert "prefers-reduced-motion:reduce" in css


@pytest.mark.smoke
def test_v213_browser_gate_persists_core_desktop_and_mobile_visual_evidence() -> None:
    script = BROWSER_GATE.read_text(encoding="utf-8")
    for path in ("/inventarios", "/captura-guiada", "/calidad-datos", "/reportes", "/informacion"):
        assert f'"{path}"' in script
    assert '("desktop-1440", 1440, 900)' in script
    assert '("mobile-390", 390, 844)' in script
    assert 'page.screenshot(path=str(screenshot), full_page=True)' in script
    assert 'if BROWSER_NAME != "chromium"' in script
    assert 'overflow-core-' in script
