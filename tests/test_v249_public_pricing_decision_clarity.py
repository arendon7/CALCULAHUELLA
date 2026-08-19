from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "app" / "templates"
STATIC = ROOT / "app" / "static"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_v249_pricing_explains_plan_fit_without_inventing_a_recommendation() -> None:
    pricing = _text(TEMPLATES / "public" / "v15" / "pricing_about.html")
    assert "IDEAL PARA" in pricing
    for fit in ("Primera huella", "Gestión continua", "Mayor exigencia"):
        assert fit in pricing
    assert "RECOMENDADO" not in pricing
    assert "v15-plan-fit" in pricing


def test_v249_visible_prices_are_explicitly_annual_platform_license_prices() -> None:
    pricing = _text(TEMPLATES / "public" / "v15" / "pricing_about.html")
    assert "licencia anual de plataforma" in pricing.lower()
    assert "Precio anual habitual" in pricing
    assert "COP / año" in pricing
    assert "COP / mes" not in pricing
    assert "servicios profesionales adicionales" in pricing.lower()
    assert "se cotizan por separado" in pricing.lower()


def test_v249_plan_ctas_remain_same_origin_and_diagnosis_led() -> None:
    pricing = _text(TEMPLATES / "public" / "v15" / "pricing_about.html")
    for label in (
        "Validar plan Esencial",
        "Evaluar plan Empresarial",
        "Revisar alcance Corporativo",
    ):
        assert label in pricing
    assert pricing.count('href="/diagnostico"') >= 3
    assert "http://" not in pricing
    assert "https://" not in pricing


def test_v249_pricing_clarity_is_presentational_only() -> None:
    css = _text(STATIC / "css" / "public-v15-fair.css")
    assert ".v15-plan-fit" in css
    assert ".v15-license-caption" in css
    pricing = _text(TEMPLATES / "public" / "v15" / "pricing_about.html").lower()
    assert "<form" not in pricing
    assert 'method="post"' not in pricing
