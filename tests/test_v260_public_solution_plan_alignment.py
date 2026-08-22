from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOLUTIONS = ROOT / "app" / "templates" / "public" / "v14" / "reduction_solutions.html"


def test_v260_solution_cards_use_current_public_plan_names_and_contextual_diagnosis_links() -> None:
    html = SOLUTIONS.read_text(encoding="utf-8")

    assert "<h3>Huella Esencial</h3>" in html
    assert "<h3>Huella Empresarial</h3>" in html
    assert "<h3>Gestión Corporativa</h3>" in html

    assert 'href="/diagnostico?plan=ESENCIAL"' in html
    assert 'href="/diagnostico?plan=EMPRESARIAL"' in html
    assert 'href="/diagnostico?plan=CORPORATIVO"' in html

    assert "<h3>Gestión de Carbono</h3>" not in html
    assert "<h3>Gestión Avanzada</h3>" not in html


def test_v260_solution_cards_preserve_review_not_verification_boundary() -> None:
    html = SOLUTIONS.read_text(encoding="utf-8")

    assert "preparación documental para revisión externa" in html
    assert "verificación independiente" not in html.casefold()
