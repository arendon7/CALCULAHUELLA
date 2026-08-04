from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"
TEMPLATES = ROOT / "app" / "templates"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_data_flow_styles_are_loaded_after_core_frontend_kit_layers():
    tokens = read(STATIC / "css" / "cth-tokens.css")
    assert '@import "./cth-data-flow.css";' in tokens
    assert tokens.index("cth-data-flow.css") > tokens.index("cth-dashboard.css")

    styles = read(STATIC / "css" / "cth-data-flow.css")
    for selector in (
        ".data-flow-nav",
        ".data-flow-list",
        ".data-flow-step.active",
        ".table-toolbox",
        ".file-intake-control",
        ".mapping-readiness.ready",
        ".batch-status-strip",
        ".row-has-error",
    ):
        assert selector in styles
    assert "@media (max-width: 620px)" in styles


def test_guided_script_builds_the_five_stage_inventory_data_flow():
    script = read(STATIC / "js" / "cth-guided.js")
    for key in ("sources", "data", "evidence", "quality", "calculation"):
        assert f"key: '{key}'" in script
    for route in (
        "/informacion#datos",
        "/informacion#evidencias",
        "/calidad-datos",
        "/calculos",
        "/cargas-operativas",
    ):
        assert route in script
    assert "initializeDataFlowNavigation" in script
    assert "aria-current', 'step'" in script
    assert "Flujo de preparación del inventario" in script


def test_file_selection_and_table_search_are_accessible_progressive_enhancements():
    script = read(STATIC / "js" / "cth-guided.js")
    assert "initializeFileIntakes" in script
    assert "aria-describedby" in script
    assert "aria-live', 'polite'" in script
    assert "initializePrimaryTableFilter" in script
    assert "input.type = 'search'" in script
    assert "normalizedSearchText" in script
    assert "initializeResponsiveTableLabels" in script
    assert "container.setAttribute('role', 'region')" in script


def test_data_routes_and_server_side_forms_remain_unchanged():
    sources = read(TEMPLATES / "sources.html")
    information = read(TEMPLATES / "information.html")
    import_data = read(TEMPLATES / "import_data.html")
    operational = read(TEMPLATES / "operational_imports.html")
    quality = read(TEMPLATES / "data_quality.html")

    assert 'action="/inventarios/{{ inventory.id }}/fuentes/nueva"' in sources
    assert 'action="/informacion/datos/nuevo"' in information
    assert 'action="/informacion/evidencias/nueva"' in information
    assert 'href="/informacion/plantilla.xlsx"' in information
    assert 'enctype="multipart/form-data"' in import_data
    assert 'action="/cargas-operativas/previsualizar"' in operational
    assert 'action="/cargas-operativas/validar"' in operational
    assert 'action="/calidad-datos/cargar"' in quality
    assert 'action="/calidad-datos/lotes/{{ summary.selected.id }}/aplicar"' in quality


def test_enhancement_is_loaded_by_authenticated_shell_only_once():
    base = read(TEMPLATES / "base.html")
    public_base = read(TEMPLATES / "public_base.html")
    assert base.count("js/cth-guided.js") == 1
    assert "js/cth-guided.js" not in public_base


def test_release_stays_v0455_until_master_assets_are_installed():
    config = read(ROOT / "app" / "config.py")
    assert 'version: str = "0.45.5"' in config
