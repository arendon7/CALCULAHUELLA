from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HERO = ROOT / "app" / "templates" / "public" / "v14" / "hero_trust.html"
EXPERIENCE = ROOT / "app" / "templates" / "public" / "v14" / "experience_resources_cta.html"
PRICING_ABOUT = ROOT / "app" / "templates" / "public" / "v15" / "pricing_about.html"


def _experience_section() -> str:
    text = EXPERIENCE.read_text(encoding="utf-8")
    start = text.index('<section class="section experience-section" id="experiencia">')
    end = text.index('<section class="section resources-section" id="recursos">')
    return text[start:end]


def _about_section() -> str:
    text = PRICING_ABOUT.read_text(encoding="utf-8")
    start = text.index('<section class="section v15-about-section" id="quienes-somos"')
    end = text.index('<section class="section v15-faq-section" id="preguntas"')
    return text[start:end]


def test_v260_public_experience_surfaces_use_capabilities_not_unverified_personal_credentials() -> None:
    hero = HERO.read_text(encoding="utf-8")
    experience = _experience_section()
    about = _about_section()
    public_experience = hero + experience + about

    assert "Criterio ambiental aplicado" in hero
    assert "datos, evidencia, metodología y decisiones" in hero
    assert "Resultado trazable" in hero

    assert "Acompañamiento técnico y profesional" in experience
    assert "criterio técnico" in experience.casefold()
    assert "Gestión de carbono" in experience
    assert "Datos y evidencias" in experience
    assert "Metodología y trazabilidad" in experience
    assert "Reducción y seguimiento" in experience

    assert "CAPACIDADES DE ACOMPAÑAMIENTO" in about
    assert "Criterio técnico integrado al proceso" in about
    assert "8 etapas" in about
    assert "1 expediente" in about

    assert "Carlos Andrés Uribe Trujillo" not in public_experience
    assert "20+" not in public_experience
    assert "Ingeniería ambiental" not in public_experience
    assert "Antropología" not in public_experience
    assert "Investigación GIEM" not in public_experience


def test_v260_public_experience_surfaces_make_documentary_claim_governance_explicit() -> None:
    experience = _experience_section()
    about = _about_section()

    for section in (experience, about):
        assert "credenciales individuales" in section
        assert "soporte documental aprobado" in section
        assert "títulos" in section
        assert "años de experiencia" in section
        assert "referencias de proyectos" in section


def test_v260_does_not_change_resources_diagnosis_pricing_or_faq_contracts() -> None:
    experience_text = EXPERIENCE.read_text(encoding="utf-8")
    about_text = PRICING_ABOUT.read_text(encoding="utf-8")

    assert '<section class="section resources-section" id="recursos">' in experience_text
    assert '<section class="diagnostic-cta" id="diagnostico">' in experience_text
    assert "Preparación para verificación" in experience_text
    assert 'data-landing-context-form' in experience_text
    assert "Solo reutilizamos sector y objetivo durante 30 minutos" in experience_text

    assert 'id="precios"' in about_text
    assert "{{ fair_discount_percent }}% DE DESCUENTO" in about_text
    assert "verificación independiente exige un tercero competente e independiente" in about_text
