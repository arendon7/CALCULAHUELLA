from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP_CSS = ROOT / "app" / "static" / "css" / "app.css"
CORE_CSS = ROOT / "app" / "static" / "css" / "v2.1-core-workflows.css"


@pytest.mark.smoke
def test_v213_core_workflow_layer_is_loaded_after_v212_product_layer() -> None:
    app_css = APP_CSS.read_text(encoding="utf-8")
    assert 'url("./v2.1-ui.css")' in app_css
    assert 'url("./v2.1-core-workflows.css")' in app_css
    assert app_css.index('url("./v2.1-ui.css")') < app_css.index('url("./v2.1-core-workflows.css")')


@pytest.mark.smoke
def test_v213_inventory_cards_prioritize_active_period_and_mobile_actions() -> None:
    css = CORE_CSS.read_text(encoding="utf-8")
    assert ".inventory-card:has(.status-chip.active)" in css
    assert ".inventory-card dl{display:grid" in css
    assert ".inventory-card .card-actions{position:sticky" in css
    assert "env(safe-area-inset-bottom)" in css


@pytest.mark.smoke
def test_v213_guided_capture_behaves_like_one_task_on_desktop_and_mobile() -> None:
    css = CORE_CSS.read_text(encoding="utf-8")
    assert ".capture-source-rail{position:sticky" in css
    assert ".capture-workspace{display:grid" in css
    assert ".capture-submit-row{position:sticky" in css
    assert ".capture-evidence-choice{grid-template-columns:1fr}" in css


@pytest.mark.smoke
def test_v213_quality_and_reports_keep_state_before_detail() -> None:
    css = CORE_CSS.read_text(encoding="utf-8")
    assert ".kpi-grid.five .kpi-card.featured" in css
    assert ".inventory-layout>aside{position:sticky" in css
    assert ".report-summary-strip>div:first-child" in css
    assert ".report-summary{position:sticky" in css
    assert ".delivery-document-card{display:flex" in css


@pytest.mark.smoke
def test_v213_dense_tables_scroll_instead_of_being_visually_crushed() -> None:
    css = CORE_CSS.read_text(encoding="utf-8")
    assert ".responsive-table{position:relative;overflow:auto" in css
    assert "overscroll-behavior-inline:contain" in css
    assert ".responsive-table th:first-child" in css
    assert "overflow-x:hidden" not in css
    assert "@media(max-width:620px)" in css
