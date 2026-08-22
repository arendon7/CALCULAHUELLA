from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPERIENCE = ROOT / "app" / "templates" / "public" / "v14" / "experience_resources_cta.html"


def _experience_section() -> str:
    text = EXPERIENCE.read_text(encoding="utf-8")
    start = text.index('<section class="section experience-section" id="experiencia">')
    end = text.index('<section class="section resources-section" id="recursos">')
    return text[start:end]


def test_v260_experience_section_uses_capabilities_not_unverified_personal_credentials() -> None:
    section = _experience_section()

    assert "Acompañamiento técnico y profesional" in section
    assert "criterio técnico" in section
    assert "Gestión de carbono" in section
    assert "Datos y evidencias" in section
    assert "Metodología y trazabilidad" in section
    assert "Reducción y seguimiento" in section

    assert "Carlos Andrés Uribe Trujillo" not in section
    assert "20+" not in section
    assert "Ingeniería ambiental" not in section
    assert "Antropología" not in section
    assert "Investigación GIEM" not in section


def test_v260_experience_section_makes_documentary_claim_governance_explicit() -> None:
    section = _experience_section()

    assert "credenciales individuales" in section
    assert "soporte documental aprobado" in section
    assert "títulos, años de experiencia ni referencias de proyectos" in section


def test_v260_does_not_change_resources_or_diagnosis_handoff_contracts() -> None:
    text = EXPERIENCE.read_text(encoding="utf-8")

    assert '<section class="section resources-section" id="recursos">' in text
    assert '<section class="diagnostic-cta" id="diagnostico">' in text
    assert "Preparación para verificación" in text
    assert 'data-landing-context-form' in text
    assert "Solo reutilizamos sector y objetivo durante 30 minutos" in text
