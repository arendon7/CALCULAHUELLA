from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.smoke
ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "app" / "static" / "css" / "v2.1-assurance-workflows.css"
APP_CSS = ROOT / "app" / "static" / "css" / "app.css"
TEMPLATES = ROOT / "app" / "templates"
BROWSER_GATE = ROOT / "scripts" / "browser_workflow_gate.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_v215_assurance_layer_is_loaded_after_decision_workflows() -> None:
    app_css = _read(APP_CSS)
    assert CSS.is_file()
    decision = '@import url("./v2.1-decision-workflows.css");'
    assurance = '@import url("./v2.1-assurance-workflows.css");'
    assert decision in app_css
    assert assurance in app_css
    assert app_css.index(decision) < app_css.index(assurance)


def test_v215_professional_control_preserves_separation_and_quality_gates() -> None:
    template = _read(TEMPLATES / "control.html")
    css = _read(CSS)
    assert "PUERTAS DE CALIDAD" in template
    assert "DECISIÓN Y CIERRE" in template
    assert "Recomendar aprobación" in template
    assert "Aprobar inventario" in template
    assert "Cerrar y bloquear inventario" in template
    assert "latest_recommendation.decided_by != user.email" in template
    assert ".v05-approval-panel" in css
    assert "position:sticky" in css


def test_v215_assurance_keeps_independence_and_material_findings_visible() -> None:
    template = _read(TEMPLATES / "assurance.html")
    css = _read(CSS)
    assert "ISO 14064-3:2019" in template
    assert "no acredita al verificador" in template
    assert "hallazgos materiales abiertos" in template
    assert "Declaración de independencia" in template
    assert "Emitir declaración controlada" in template
    assert ".methodology-boundary" in css
    assert "#hallazgos .responsive-table" in css


def test_v215_verification_prioritizes_readiness_findings_and_reproducible_package() -> None:
    template = _read(TEMPLATES / "verification.html")
    css = _read(CSS)
    assert "Estado previo al aseguramiento" in template
    assert "HALLAZGOS EXTERNOS" in template
    assert "PAQUETE DE ASEGURAMIENTO" in template
    assert "Exportación reproducible" in template
    assert "PRIORIDAD DE VERIFICACIÓN" in template
    assert "Resolver bloqueos de calidad antes de concluir" in template
    assert "Resolver hallazgos materiales abiertos" in template
    assert "Generar el paquete reproducible para iniciar la revisión" in template
    assert 'id="puertas"' in template
    assert 'id="hallazgos"' in template
    assert 'id="paquete"' in template
    assert "Funcional · V0.8" not in template
    assert ".verification-side" in css
    assert ".finding-card" in css
    assert ".verification-main .table-wrap" in css


def test_v215_methodology_closure_keeps_truth_boundaries_and_approval_controls() -> None:
    template = _read(TEMPLATES / "methodology_closure.html")
    css = _read(CSS)
    assert "no se netean automáticamente" in template
    assert "Preparación metodológica" in template
    assert "Aprobar política" in template
    assert "PUERTAS DE CIERRE" in template
    assert "Siguiente decisión metodológica" in template
    assert 'id="puertas-cierre"' in template
    assert "Alcance 2" in template
    assert "Metodología / Cierre V0.32" not in template
    assert "V0.32 ·" not in template
    assert template.index("PUERTAS DE CIERRE") < template.index("DECISIONES VERSIONADAS")
    assert ".methodology-policy-form .table-actions" in css
    assert "#anio-base .responsive-table" in css


def test_v215_methodology_governance_preserves_version_and_snapshot_traceability() -> None:
    template = _read(TEMPLATES / "methodology_governance.html")
    css = _read(CSS)
    assert "Versiones metodológicas" in template
    assert "Congelar configuración" in template
    assert "Snapshots por inventario" in template
    assert "Política de cierre metodológico" in template
    assert "{{ row.snapshot_name }}" not in template
    assert "content_hash" in template
    assert ".settings-list article" in css
    assert ".panel > .table-wrap" in css


def test_v215_mobile_contract_contains_dense_assurance_surfaces_without_hiding_overflow() -> None:
    css = _read(CSS)
    assert "@media(max-width:760px)" in css
    assert "min-width:0" in css
    assert "overflow-x:auto" in css
    assert "overscroll-behavior-inline:contain" in css
    assert "overflow-x:hidden" not in css
    assert "safe-area-inset-bottom" in css


def test_v215_visual_gate_covers_assurance_and_methodology_surfaces() -> None:
    gate = _read(BROWSER_GATE)
    for slug, route in (
        ("control-profesional", "/control"),
        ("aseguramiento", "/aseguramiento"),
        ("verificacion", "/verificacion"),
        ("cierre-metodologico", "/metodologia/cierre"),
        ("gobierno-metodologico", "/gobierno-metodologico"),
    ):
        assert f'("{slug}", "{route}")' in gate
