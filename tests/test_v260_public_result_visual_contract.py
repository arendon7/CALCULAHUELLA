from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "app" / "templates" / "public_base.html"
RESULT = ROOT / "app" / "templates" / "public_thanks.html"
CSS = ROOT / "app" / "static" / "css" / "public-diagnosis-result.css"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_v260_public_result_loads_dedicated_visual_contract() -> None:
    base = _text(BASE)
    result = _text(RESULT)
    css = _text(CSS)

    assert "css/public-diagnosis-result.css" in base
    assert 'class="result-shell intelligent-result"' in result
    assert 'class="result-grid four"' in result
    assert 'class="public-result-columns"' in result
    assert 'class="result-route"' in result

    assert ".intelligent-result .result-grid.four" in css
    assert "grid-template-columns: repeat(4, minmax(0, 1fr))" in css
    assert ".public-result-columns" in css
    assert "grid-template-columns: repeat(3, minmax(0, 1fr))" in css


def test_v260_public_result_visual_contract_has_mobile_fallbacks() -> None:
    css = _text(CSS)

    assert "@media (max-width: 980px)" in css
    assert "@media (max-width: 620px)" in css
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in css
    assert ".public-result-columns" in css
    assert "grid-template-columns: 1fr" in css
    assert ".intelligent-result .result-actions .button" in css
    assert "width: 100%" in css
