from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "app" / "templates"
STATIC = ROOT / "app" / "static"


def read_template(name: str) -> str:
    return (TEMPLATES / name).read_text(encoding="utf-8")


def test_outcome_layer_is_loaded_from_base_and_tokens():
    base = read_template("base.html")
    tokens = (STATIC / "css" / "cth-tokens.css").read_text(encoding="utf-8")
    css = (STATIC / "css" / "cth-outcomes.css").read_text(encoding="utf-8")

    assert "js/cth-outcomes.js" in base
    assert '@import "./cth-outcomes.css";' in tokens
    assert ".outcome-flow-nav" in css
    assert ".outcome-context" in css
    assert ".outcome-card-toolbox" in css
    assert '.progress[role="progressbar"]' in css
    assert "@media (max-width: 760px)" in css


def test_outcome_navigation_connects_five_decision_stages_without_overlap():
    javascript = (STATIC / "js" / "cth-outcomes.js").read_text(encoding="utf-8")

    for title, route in (
        ("Cálculo", "/calculos"),
        ("Control", "/control"),
        ("Informes", "/reportes"),
        ("Reducción", "/reduccion"),
        ("Escenarios", "/escenarios"),
    ):
        assert f"title: '{title}'" in javascript
        assert f"href: '{route}'" in javascript

    assert "Flujo de resultados y decisiones" in javascript
    assert "aria-current" in javascript
    assert "document.querySelector('[data-data-flow-nav]')?.remove()" in javascript
    assert "document.body.classList.add('outcome-page')" in javascript


def test_outcome_layer_adds_accessible_progress_and_local_search():
    javascript = (STATIC / "js" / "cth-outcomes.js").read_text(encoding="utf-8")

    assert "role', 'progressbar'" in javascript
    assert "aria-valuenow" in javascript
    assert "enhanceScenarioTracks" in javascript
    assert "normalize('NFD')" in javascript
    assert "initializeOutcomeCardFilters" in javascript
    assert "initializeOutcomeTableFilter" in javascript
    assert "Buscar medidas de reducción" in javascript
    assert "Buscar observaciones de revisión" in javascript
    assert "Buscar tipo, versión, estado, autor o fecha" in javascript


def test_calculation_and_control_contracts_remain_functional():
    calculations = read_template("calculations.html")
    control = read_template("control.html")

    assert 'action="/inventarios/{{ inventory.id }}/recalcular"' in calculations
    assert 'href="/fuentes/{{ row.source.id }}"' in calculations
    assert "Cómo calcula esta versión" in calculations

    for action in (
        "/control/inventario/enviar-revision",
        "/control/inventario/recomendar",
        "/control/inventario/aprobar",
        "/control/inventario/cerrar",
        "/control/observaciones/nueva",
    ):
        assert f'action="{action}"' in control
    assert "/control/observaciones/{{ observation.id }}/responder" in control
    assert "/control/observaciones/{{ observation.id }}/cerrar" in control


def test_reports_reduction_and_scenarios_keep_operational_actions():
    reports = read_template("reports.html")
    reduction = read_template("reduction.html")
    scenarios = read_template("scenarios.html")

    assert 'action="/reportes/generar"' in reports
    assert 'href="/reportes/{{ item.id }}/descargar"' in reports
    assert 'action="/reportes/{{ item.id }}/aprobar"' in reports

    for action in (
        "/reduccion/acciones/nueva",
        "/reduccion/acciones/{{ action.id }}/actualizar",
        "/reduccion/metas/nueva",
        "/reduccion/metas/{{ target.id }}/actualizar",
        "/reduccion/metas/{{ target.id }}/sincronizar",
    ):
        assert f'action="{action}"' in reduction
    assert 'href="/escenarios"' in reduction

    assert 'action="/escenarios/{{ selected.id }}/configurar"' in scenarios
    assert 'action="/escenarios/nuevo"' in scenarios
    assert "CURVA DE COSTO MARGINAL" in scenarios
    assert "EMISIONES PROYECTADAS" in scenarios
