from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROCESS = ROOT / "app" / "templates" / "public" / "v14" / "process_trace.html"
PUBLIC_CSS = ROOT / "app" / "static" / "css" / "public-v1.6.css"
PUBLIC_V16_JS = ROOT / "app" / "static" / "js" / "public-v1.6.js"
PUBLIC_BASE = ROOT / "app" / "templates" / "public_base.html"


def test_public_process_exposes_exactly_eight_canonical_stages():
    html = PROCESS.read_text(encoding="utf-8")
    assert html.count('class="process-step') == 8
    expected = [
        "Diagnóstico",
        "Planificación",
        "Datos y evidencias",
        "Metodología",
        "Cálculo",
        "Revisión",
        "Informe y cierre",
        "Reducción",
    ]
    steps = [
        line.split("<b>", 1)[1].split("</b>", 1)[0]
        for line in html.splitlines()
        if 'class="process-step' in line and "<b>" in line
    ]
    assert steps == expected
    for number in range(1, 9):
        assert f"ETAPA {number}" in html


def test_public_process_has_methodology_as_independent_stage():
    html = PROCESS.read_text(encoding="utf-8")
    assert 'data-process="metodologia"' in html
    assert 'data-process-panel="metodologia"' in html
    assert "Factores versionados" in html
    assert "Supuestos y exclusiones" in html


def test_public_process_grid_supports_eight_stages_responsively():
    css = PUBLIC_CSS.read_text(encoding="utf-8")
    assert ".process-nav{grid-template-columns:repeat(8,1fr)}" in css
    assert "repeat(4,1fr)" in css
    assert "repeat(2,1fr)" in css


def test_v16_public_javascript_knows_all_process_keys_and_core_interactions():
    js = PUBLIC_V16_JS.read_text(encoding="utf-8")
    for key in (
        "diagnostico",
        "configuracion",
        "recopilacion",
        "metodologia",
        "calculo",
        "revision",
        "informes",
        "accion",
    ):
        assert f"{key}:" in js
    for contract in (
        "data-menu-button",
        "data-tab",
        "data-process",
        "data-trace",
        "data-landing-context-form",
        "data-resource",
    ):
        assert contract in js


def test_public_base_loads_single_v16_public_asset_authority_and_hides_historical_badge():
    html = PUBLIC_BASE.read_text(encoding="utf-8")
    assert "public-v1.6.css" in html
    assert "public-v1.4.css" not in html
    assert html.count("public-v1.6.css") == 1
    assert "public-v1.6.js" in html
    assert "public-v1.4.js" not in html
    assert html.count("public-v1.6.js") == 1
    assert "V1.4.0 integración controlada" not in html
    assert "no actúa automáticamente como organismo verificador o certificador" in html
