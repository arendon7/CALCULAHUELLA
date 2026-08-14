from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]
APP_CSS = ROOT / "app" / "static" / "css" / "app.css"
DECISION_CSS = ROOT / "app" / "static" / "css" / "v2.1-decision-workflows.css"
CALCULATIONS = ROOT / "app" / "templates" / "calculations.html"
ANALYSIS = ROOT / "app" / "templates" / "analysis.html"
REDUCTION = ROOT / "app" / "templates" / "reduction.html"
PERIOD_CLOSE = ROOT / "app" / "templates" / "period_close.html"


def _login(client: TestClient) -> None:
    response = client.post(
        "/login",
        data={"email": "consultor@calculatuhuella.local", "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def _pulse_total(html: str) -> str:
    match = re.search(r'class="inventory-pulse-total".*?<strong>([^<]+)</strong>', html, re.S)
    assert match is not None
    return match.group(1).strip()


@pytest.mark.smoke
def test_v213_data_workflow_layer_loads_after_core_workflows() -> None:
    app_css = APP_CSS.read_text(encoding="utf-8")
    assert 'url("./v2.1-data-workflows.css")' in app_css
    assert 'url("./v2.1-decision-workflows.css")' in app_css
    assert app_css.index('url("./v2.1-data-workflows.css")') < app_css.index('url("./v2.1-decision-workflows.css")')


@pytest.mark.smoke
def test_v214_calculation_prioritizes_result_then_engine_health_before_trace_table() -> None:
    template = CALCULATIONS.read_text(encoding="utf-8")
    css = DECISION_CSS.read_text(encoding="utf-8")
    assert 'class="inventory-pulse card calculation-result-pulse"' in template
    assert "HUELLA BRUTA DEL PERIODO" in template
    assert 'id="salud-calculo"' in template
    assert 'class="source-summary-grid calculation-kpis"' in template
    assert 'id="trazabilidad-calculo"' in template
    assert 'class="card engine-rules"' in template
    assert template.index("calculation-result-pulse") < template.index("calculation-notice")
    assert template.index("calculation-notice") < template.index("calculation-kpis")
    assert template.index("calculation-kpis") < template.index('id="trazabilidad-calculo"')
    assert ".calculation-kpis .mini-card:nth-child(4)" in css
    assert ".calculation-kpis+.card table{min-width:900px}" in css
    assert ".engine-rules .rule-grid{display:grid" in css


@pytest.mark.smoke
def test_v214_calculation_uses_same_canonical_gross_total_as_dashboard() -> None:
    with TestClient(app) as client:
        _login(client)
        dashboard = client.get("/dashboard")
        results = client.get("/calculos")
        assert dashboard.status_code == 200
        assert results.status_code == 200
        assert "HUELLA BRUTA DEL PERIODO" in results.text
        assert "Remociones, emisiones evitadas, compensaciones" in results.text
        assert _pulse_total(results.text) == _pulse_total(dashboard.text)


@pytest.mark.smoke
def test_v214_analysis_keeps_hotspots_and_executive_reading_above_history() -> None:
    template = ANALYSIS.read_text(encoding="utf-8")
    css = DECISION_CSS.read_text(encoding="utf-8")
    assert 'class="analysis-grid"' in template
    assert 'class="card insight-panel"' in template
    assert 'class="card history-card"' in template
    assert ".analysis-grid .insight-panel" in css
    assert ".rank-list>article{display:grid" in css
    assert ".analysis-grid .insight-panel{order:-1}" in css


@pytest.mark.smoke
def test_v214_reduction_keeps_primary_decision_target_gap_and_portfolio_hierarchy() -> None:
    template = REDUCTION.read_text(encoding="utf-8")
    css = DECISION_CSS.read_text(encoding="utf-8")
    for marker in (
        'class="reduction-command card"',
        'class="reduction-kpis"',
        'class="card target-command"',
        'class="portfolio-table-wrap"',
        'class="reduction-create-grid"',
    ):
        assert marker in template
    assert ".reduction-command{display:grid" in css
    assert ".reduction-kpis{display:grid" in css
    assert ".target-command-grid{display:grid" in css
    assert ".portfolio-table-wrap{width:100%;min-width:0;max-width:100%;overflow:auto" in css


@pytest.mark.smoke
def test_v214_period_close_keeps_readiness_blockers_before_irreversible_actions() -> None:
    template = PERIOD_CLOSE.read_text(encoding="utf-8")
    css = DECISION_CSS.read_text(encoding="utf-8")
    assert 'class="period-status-bar"' in template
    assert 'class="card blockers-card"' in template
    assert 'class="card action-card"' in template
    assert ".period-status-bar{display:grid" in css
    assert ".period-layout{display:grid" in css
    assert ".period-side{position:sticky" in css
    assert ".danger-zone" in css


@pytest.mark.smoke
def test_v214_decision_workflows_collapse_without_masking_overflow() -> None:
    css = DECISION_CSS.read_text(encoding="utf-8")
    assert "@media(max-width:900px)" in css
    assert "@media(max-width:620px)" in css
    assert ".analysis-detail-grid,body.app-shell .management-grid,body.app-shell .target-command-grid,body.app-shell .period-layout{grid-template-columns:1fr}" in css
    assert ".portfolio-table{min-width:1180px}" in css
    assert ".period-table{min-width:1040px}" in css
    assert "overflow-x:hidden" not in css
    assert "prefers-reduced-motion:reduce" in css
