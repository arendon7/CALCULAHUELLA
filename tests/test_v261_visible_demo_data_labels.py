from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V14 = ROOT / "app" / "templates" / "public" / "v14"
V15 = ROOT / "app" / "templates" / "public" / "v15"
BROWSER_GATE = ROOT / "scripts" / "browser_public_funnel_gate.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_v261_html_mocks_label_demonstrative_data_visibly() -> None:
    hero = _read(V14 / "hero_trust.html")
    platform = _read(V14 / "problem_platform.html")
    process = _read(V14 / "process_trace.html")
    reports = _read(V14 / "reports_decision.html")
    reduction = _read(V14 / "reduction_solutions.html")

    assert '<span class="app-title">Centro de trabajo</span>' in hero
    assert '<span class="app-kicker demo-data-label">DATOS DEMOSTRATIVOS</span>' in hero
    assert "Greenatics S.A.S. · DATOS DEMOSTRATIVOS" in platform
    assert "Calcula tu Huella · DATOS DEMOSTRATIVOS" in process
    assert "Datos demostrativos:" in process
    assert "DATOS DEMOSTRATIVOS · INFORME EJECUTIVO · 2026" in reports
    assert "Sala de decisión · DATOS DEMOSTRATIVOS" in reports
    assert "DATOS DEMOSTRATIVOS · PLAN DE REDUCCIÓN 2026–2027" in reduction


def test_v261_demo_labels_preserve_mock_status_semantics() -> None:
    hero = _read(V14 / "hero_trust.html")
    platform = _read(V14 / "problem_platform.html")
    reports = _read(V14 / "reports_decision.html")
    reduction = _read(V14 / "reduction_solutions.html")

    assert '<span class="status-chip">En recopilación</span>' in hero
    assert '<div class="app-kicker">Tu inventario</div>' in hero
    assert "Greenatics S.A.S. · Periodo 2026 · Uso interno" in hero
    assert '<span class="status-chip">En preparación</span>' in platform
    assert "Aprobado internamente" in reports
    assert "En evaluación" in reduction
    assert "Priorizada" in reduction
    assert "En ejecución" in reduction
    assert "Seguimiento" in reduction


def test_v261_demo_label_does_not_reclassify_real_commercial_content() -> None:
    pricing = _read(V15 / "pricing_about.html")
    proof = _read(V15 / "product_proof.html")
    reduction = _read(V14 / "reduction_solutions.html")

    assert "DATOS DEMOSTRATIVOS" not in pricing
    assert "Los datos visibles son demostrativos." in proof

    solution_section = reduction.split('<section class="section section-soft" id="soluciones">', 1)[1]
    assert "DATOS DEMOSTRATIVOS" not in solution_section
    assert "<h3>Huella Esencial</h3>" in solution_section
    assert "<h3>Huella Empresarial</h3>" in solution_section
    assert "<h3>Gestión Corporativa</h3>" in solution_section


def test_v261_browser_gate_requires_visible_demo_transparency() -> None:
    source = _read(BROWSER_GATE)

    assert "def _assert_demo_transparency(page: Page)" in source
    assert 'page.locator(".app-top .demo-data-label")' in source
    assert 'page.locator(".workspace-bar")' in source
    assert 'page.locator(".process-window-top")' in source
    assert 'page.locator(".report-page-front")' in source
    assert 'page.locator(".decision-top")' in source
    assert 'page.locator(".reduction-head")' in source
    assert "Etiqueta demostrativa del hero quedó recortada" in source
    assert 'landing-demo-transparency.png' in source
