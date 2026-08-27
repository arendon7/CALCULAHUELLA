from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK_TEMPLATE = ROOT / "app" / "templates" / "work_items.html"
WORK_CSS = ROOT / "app" / "static" / "css" / "work-items.css"
BROWSER_GATE = ROOT / "scripts" / "browser_workflow_gate.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_v262_operational_summary_precedes_support_actions_in_dom() -> None:
    source = _read(WORK_TEMPLATE)

    heading = source.index('<section class="page-heading work-page-heading">')
    summary = source.index('<section class="work-summary" aria-label="Resumen de trabajo">')
    support_actions = source.index('<div class="work-secondary-actions" aria-label="Acciones de apoyo">')
    work_layout = source.index('<section class="work-layout">')

    assert heading < summary < support_actions < work_layout
    assert 'class="page-actions"' not in source


def test_v262_support_actions_remain_present_and_keep_route_semantics() -> None:
    source = _read(WORK_TEMPLATE)

    assert source.count('href="/dashboard"') == 1
    assert source.count('href="/guia"') >= 1
    assert source.count('action="/mi-trabajo/sincronizar"') == 1
    assert 'name="return_status" value="{{ selected_status }}"' in source
    assert 'name="return_stage" value="{{ selected_stage }}"' in source
    assert 'name="return_scope" value="{{ selected_scope }}"' in source
    assert 'name="return_inventory_id" value="{{ selected_inventory_filter }}"' in source


def test_v262_mobile_summary_is_compact_without_hiding_support_actions() -> None:
    css = _read(WORK_CSS)

    assert '.work-secondary-actions{display:flex' in css
    assert '@media(max-width:640px)' in css
    assert '.work-summary{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin:10px 0 14px}' in css
    assert '.work-metric{border-radius:14px;padding:11px 12px}' in css
    assert '.work-metric strong{font-size:1.35rem;margin-top:3px}' in css
    assert '.work-secondary-actions{display:grid;grid-template-columns:1fr;gap:8px;margin:0 0 14px}' in css
    assert '.work-secondary-actions form,.work-secondary-actions .btn,.work-secondary-actions form .btn{width:100%;max-width:100%}' in css


def test_v262_browser_gate_keeps_exact_mobile_evidence_viewports() -> None:
    source = _read(BROWSER_GATE)

    assert '("mobile-390", 390, 844)' in source
    assert '("mobile-360", 360, 800)' in source
    assert 'page.screenshot(path=str(screenshot), full_page=True)' in source
    assert 'overflow_failures = [row for row in result["viewports"] if row["overflow_px"] > 1]' in source
