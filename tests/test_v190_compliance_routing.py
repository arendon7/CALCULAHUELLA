from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.compliance_web import compliance_score
from app.main import app

ROOT = Path(__file__).resolve().parents[1]

COMPLIANCE_ROUTES = {
    ("GET", "/cumplimiento"),
    ("POST", "/cumplimiento/{assessment_id}/actualizar"),
}


def test_v190_compliance_has_dedicated_http_and_score_authority():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    module_source = (ROOT / "app/compliance_web.py").read_text(encoding="utf-8")
    executive_source = (ROOT / "app/executive_portfolio_web.py").read_text(encoding="utf-8")
    assert 'def _compliance_score' not in main_source
    assert '@app.get("/cumplimiento"' not in main_source
    assert '@app.post("/cumplimiento/' not in main_source
    assert "register_compliance_routes(" in main_source
    assert module_source.count("@app.") == 2
    assert "def compliance_score" in module_source
    assert "from .compliance_web import compliance_score" in executive_source
    assert "_compliance_score" not in executive_source
    assert '@app.get("/gobierno-metodologico"' not in module_source


def test_v190_compliance_route_contract_is_unique_and_complete():
    actual = []
    relevant = {path for _, path in COMPLIANCE_ROUTES}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if path in relevant:
            actual.extend((method, path) for method in methods if method in {"GET", "POST"})
    assert set(actual) == COMPLIANCE_ROUTES
    assert len(actual) == len(COMPLIANCE_ROUTES)


def test_v190_compliance_score_preserves_weights_and_no_aplica_exclusion():
    rows = [
        SimpleNamespace(status="Cumple"),
        SimpleNamespace(status="Parcial"),
        SimpleNamespace(status="Pendiente"),
        SimpleNamespace(status="No cumple"),
        SimpleNamespace(status="No aplica"),
    ]
    assert compliance_score(rows) == 38
    assert compliance_score([SimpleNamespace(status="No aplica")]) == 0
