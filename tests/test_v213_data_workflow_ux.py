from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP_CSS = ROOT / "app" / "static" / "css" / "app.css"
DATA_CSS = ROOT / "app" / "static" / "css" / "v2.1-data-workflows.css"
BROWSER_GATE = ROOT / "scripts" / "browser_workflow_gate.py"
INFORMATION = ROOT / "app" / "templates" / "information.html"
SOURCES = ROOT / "app" / "templates" / "sources.html"
SOURCE = ROOT / "app" / "templates" / "source.html"


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
    assert 'href="/captura-guiada"' in template
    for target in ('data-task-target="datos"', 'data-task-target="solicitudes"', 'data-task-target="evidencias"'):
        assert target in template
    assert ".task-jumpbar{position:sticky" in css
    assert ".request-list>article{position:relative;display:grid" in css
    assert ".information-layout>.sticky-form{position:sticky" in css


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
def test_source_detail_keeps_traceability_before_methodological_depth() -> None:
    template = SOURCE.read_text(encoding="utf-8")
    css = DATA_CSS.read_text(encoding="utf-8")
    assert 'class="calculation-notice notice-success"' in template
    assert 'data-default-task="datos"' in template
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
