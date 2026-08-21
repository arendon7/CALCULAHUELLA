from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "app" / "templates" / "public" / "v14" / "reduction_solutions.html"


def _solutions(text: str) -> str:
    return text.split('id="soluciones"', 1)[1]


def test_v260_solution_cards_use_current_public_plan_names() -> None:
    text = _solutions(TEMPLATE.read_text(encoding="utf-8"))

    for name in ("Huella Esencial", "Huella Empresarial", "Gestión Corporativa"):
        assert name in text

    assert "Gestión de Carbono" not in text
    assert "Gestión Avanzada" not in text


def test_v260_solution_cards_preserve_plan_context_into_diagnosis() -> None:
    text = _solutions(TEMPLATE.read_text(encoding="utf-8"))

    for code in ("ESENCIAL", "EMPRESARIAL", "CORPORATIVO"):
        assert f'href="/diagnostico?plan={code}"' in text

    assert 'href="/diagnostico"' not in text


def test_v260_alignment_does_not_strengthen_verification_claims() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")

    assert "preparación documental para revisión externa" in text
    assert "revisión interna y eventual verificación externa" in text
    assert "verificación independiente incluida" not in text.lower()
