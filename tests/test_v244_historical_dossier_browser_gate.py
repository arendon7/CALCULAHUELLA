from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BROWSER_GATE = ROOT / "scripts" / "browser_workflow_gate.py"


def test_v244_browser_gate_exercises_historical_dossier_on_desktop_and_mobile() -> None:
    script = BROWSER_GATE.read_text(encoding="utf-8")

    assert "HISTORICAL_DOSSIER_VIEWPORTS" in script
    assert '("desktop-1440", 1440, 900)' in script
    assert '("mobile-390", 390, 844)' in script
    assert "_historical_dossier_contract(page)" in script
    assert ".inventory-card.historical-context" in script


def test_v244_browser_gate_locks_all_seven_scoped_routes() -> None:
    script = BROWSER_GATE.read_text(encoding="utf-8")

    expected = [
        '"/informacion"',
        '"/calculos"',
        '"/analisis"',
        '"/reduccion"',
        '"/reportes"',
        '"/entrega-profesional"',
    ]
    for fragment in expected:
        assert fragment in script
    assert "expected_hrefs" in script
    assert "data-inventory-dossier-nav" in script


def test_v244_browser_gate_proves_global_period_preservation_and_mobile_visibility() -> None:
    script = BROWSER_GATE.read_text(encoding="utf-8")

    assert 'data-period-preserving="true"' in script
    assert 'href="{dossier_root}/informacion"' in script
    assert "period_preserving_hrefs" in script
    assert "navigation_overflow_px" in script
    assert "Las siete vistas históricas no permanecen visibles en móvil" in script
    assert "Resultados perdió el periodo histórico" in script
