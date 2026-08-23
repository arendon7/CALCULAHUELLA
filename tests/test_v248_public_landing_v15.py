from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.public_web import FAIR_DISCOUNT_PERCENT, _fair_offer


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "app" / "templates"
STATIC = ROOT / "app" / "static"
SEED_DEFAULTS = ROOT / "app" / "seed_defaults.py"
PUBLIC_WEB = ROOT / "app" / "public_web.py"


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
    assert "css/public-v15-fair.css" in base
    assert 'class="public-v14-body public-v15-body"' in base
    nav = base.split('<nav class="nav-links"', 1)[1].split("</nav>", 1)[0]
    assert nav.count("<a ") == 4
    for href in ("/#como-funciona", "/#plataforma", "/#informes", "/#soluciones"):
        assert href in nav
    assert "/#precios" not in nav
    assert 'href="#precios">Ver planes y precios' in audience
    assert "/#precios" in base
    assert "Potenciado por GREENATICS" in base


def test_v248_fair_campaign_is_annual_and_preserves_verification_boundary() -> None:
    pricing = _text(TEMPLATES / "public" / "v15" / "pricing_about.html")
    assert '{% for offer in fair_offers %}' in pricing
    for token in (
        "offer.regular_annual_fee",
        "offer.promo_annual_fee",
        "offer.discount_percent",
        "plan.max_users",
        "plan.max_facilities",
        "plan.max_inventories",
        "plan.includes_scope3",
        "plan.includes_verification_portal",
    ):
        assert token in pricing
    assert "plan.monthly_fee" not in pricing
    assert "plan.annual_fee" not in pricing
    assert "COP / año" in pricing
    assert "COP / mes" not in pricing
    assert "{{ fair_discount_percent }}% DE DESCUENTO" in pricing
    assert "Feria de Negocios Verdes de Corantioquia" in pricing
    assert "img/campaign/corantioquia.png" in pricing
    assert 'id="precios"' in pricing
    assert "no equivalen a verificación independiente" in pricing
    assert "tercero verificador" in pricing


def test_v248_fair_offer_calculates_approved_annual_prices_without_mutating_plan() -> None:
    assert FAIR_DISCOUNT_PERCENT == 30
    expected = {
        "ESENCIAL": (390000, 273000),
        "EMPRESARIAL": (990000, 693000),
        "CORPORATIVO": (2490000, 1743000),
    }
    for code, (regular, promo) in expected.items():
        plan = SimpleNamespace(code=code, monthly_fee=regular, annual_fee=regular * 10)
        offer = _fair_offer(plan)
        assert offer["regular_annual_fee"] == regular
        assert offer["promo_annual_fee"] == promo
        assert offer["discount_percent"] == 30
        assert plan.monthly_fee == regular
        assert plan.annual_fee == regular * 10

    seed = _text(SEED_DEFAULTS)
    assert '("ESENCIAL", "Huella Esencial", "Una sede, alcances 1 y 2, informe ejecutivo y acompañamiento básico.", 390000, 3900000,' in seed
    assert '("EMPRESARIAL", "Huella Empresarial", "Hasta cinco sedes, alcance 3 priorizado, informes técnicos y gestión anual.", 990000, 9900000,' in seed
    assert '("CORPORATIVO", "Gestión Corporativa", "Operación multiempresa, alcance 3 avanzado, verificación, integraciones y soporte prioritario.", 2490000, 24900000,' in seed
    assert "without mutating billing semantics" in _text(PUBLIC_WEB)


def test_v248_campaign_uses_local_corantioquia_asset() -> None:
    logo = STATIC / "img" / "campaign" / "corantioquia.png"
    assert logo.exists()
    assert logo.stat().st_size > 0


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
    assert "Software climático con criterio ambiental detrás" in about
    assert "sin presentar el software como sustituto del juicio profesional" in about
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
