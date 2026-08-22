from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V14 = ROOT / "app" / "templates" / "public" / "v14"
V15 = ROOT / "app" / "templates" / "public" / "v15"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_v261_html_mocks_label_demonstrative_data_visibly() -> None:
    hero = _read(V14 / "hero_trust.html")
    platform = _read(V14 / "problem_platform.html")
    process = _read(V14 / "process_trace.html")
    reports = _read(V14 / "reports_decision.html")
    reduction = _read(V14 / "reduction_solutions.html")

    assert "DATOS DEMOSTRATIVOS" in hero
    assert "Greenatics S.A.S. · DATOS DEMOSTRATIVOS" in platform
    assert "Calcula tu Huella · DATOS DEMOSTRATIVOS" in process
    assert "Datos demostrativos:" in process
    assert "DATOS DEMOSTRATIVOS · INFORME EJECUTIVO · 2026" in reports
    assert "Sala de decisión · DATOS DEMOSTRATIVOS" in reports
    assert "DATOS DEMOSTRATIVOS · PLAN DE REDUCCIÓN 2026–2027" in reduction


def test_v261_demo_label_does_not_reclassify_real_commercial_content() -> None:
    pricing = _read(V15 / "pricing_about.html")
    proof = _read(V15 / "product_proof.html")
    reduction = _read(V14 / "reduction_solutions.html")

    assert "DATOS DEMOSTRATIVOS" not in pricing
    assert "Los datos visibles son demostrativos." in proof

    # Solo el mock de reducción es demostrativo; las tarjetas comerciales siguen siendo oferta real.
    solution_section = reduction.split('<section class="section section-soft" id="soluciones">', 1)[1]
    assert "DATOS DEMOSTRATIVOS" not in solution_section
    assert "<h3>Huella Esencial</h3>" in solution_section
    assert "<h3>Huella Empresarial</h3>" in solution_section
    assert "<h3>Gestión Corporativa</h3>" in solution_section
