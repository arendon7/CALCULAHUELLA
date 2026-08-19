from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "app" / "templates"
STATIC = ROOT / "app" / "static"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_v248_landing_keeps_v14_authority_and_adds_v15_layers_in_order() -> None:
    home = _text(TEMPLATES / "public_home.html")
    expected = [
        'public/v14/hero_trust.html',
        'public/v15/audience_value.html',
        'public/v14/problem_platform.html',
        'public/v14/process_trace.html',
        'public/v15/product_proof.html',
        'public/v14/reports_decision.html',
        'public/v14/reduction_solutions.html',
        'public/v15/pricing_about.html',
        'public/v14/experience_resources_cta.html',
    ]
    positions = [home.index(item) for item in expected]
    assert positions == sorted(positions)
    assert "Toda tu gestión de carbono, conectada" in home


def test_v248_pricing_is_prominent_without_expanding_primary_navigation() -> None:
    base = _text(TEMPLATES / "public_base.html")
    audience = _text(TEMPLATES / "public" / "v15" / "audience_value.html")
    assert "css/public-v15.css" in base
    assert 'class="public-v14-body public-v15-body"' in base
    nav = base.split('<nav class="nav-links"', 1)[1].split("</nav>", 1)[0]
    assert nav.count("<a ") == 4
    for href in ("/#como-funciona", "/#plataforma", "/#informes", "/#soluciones"):
        assert href in nav
    assert "/#precios" not in nav
    assert 'href="#precios">Ver planes y precios' in audience
    assert "/#precios" in base
    assert "Potenciado por GREENATICS" in base


def test_v248_pricing_uses_service_plan_authority_and_preserves_verification_boundary() -> None:
    pricing = _text(TEMPLATES / "public" / "v15" / "pricing_about.html")
    assert '{% for plan in plans %}' in pricing
    for token in (
        "plan.monthly_fee",
        "plan.annual_fee",
        "plan.max_users",
        "plan.max_facilities",
        "plan.max_inventories",
        "plan.includes_scope3",
        "plan.includes_verification_portal",
    ):
        assert token in pricing
    assert 'id="precios"' in pricing
    assert "no equivalen a verificación independiente" in pricing
    assert "tercero verificador" in pricing
    assert "Valores de referencia en COP" in pricing


def test_v248_product_proof_reuses_real_repository_screenshots() -> None:
    proof = _text(TEMPLATES / "public" / "v15" / "product_proof.html")
    for filename in ("dashboard.png", "captura.png", "recorrido.png", "diccionario.png", "movil.png"):
        assert f"img/product-proof/{filename}" in proof
        path = STATIC / "img" / "product-proof" / filename
        assert path.exists()
        assert path.stat().st_size > 0
    assert "Los datos visibles son demostrativos" in proof
    assert "La interfaz sigue evolucionando" in proof


def test_v248_about_copy_does_not_turn_internal_review_into_independent_verification() -> None:
    about = _text(TEMPLATES / "public" / "v15" / "pricing_about.html")
    legacy_authority = _text(TEMPLATES / "public" / "v14" / "experience_resources_cta.html")
    assert "Software climático con experiencia ambiental detrás" in about
    assert "no presentar el software como sustituto del juicio profesional" in about
    assert "verificación documental correspondiente" in about
    assert "verificación documental correspondiente" in legacy_authority
    assert "certifica automáticamente" not in about.lower()


def test_v248_new_sections_remain_get_only_content_surfaces() -> None:
    for name in ("audience_value.html", "product_proof.html", "pricing_about.html"):
        text = _text(TEMPLATES / "public" / "v15" / name).lower()
        assert "<form" not in text
        assert 'method="post"' not in text
        assert "http://" not in text
        assert "https://" not in text
