import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "app" / "templates"
STATIC = ROOT / "app" / "static"


def read(name: str) -> str:
    return (TEMPLATES / name).read_text(encoding="utf-8")


def test_brand_compatibility_assets_are_present_and_used():
    for name in ("brand-primary.svg", "brand-reversed.svg", "brand-symbol.svg", "brand-manifest.json"):
        assert (STATIC / "img" / name).exists()
    combined = "\n".join(read(name) for name in ("base.html", "public_base.html", "login.html", "supplier_portal.html"))
    assert "img/brand-primary.svg" in combined
    assert "img/brand-reversed.svg" in combined
    assert "img/brand-symbol.svg" in combined


def test_public_experience_has_mobile_navigation_and_official_claim():
    base = read("public_base.html")
    home = read("public_home.html")
    assert 'id="publicMenuButton"' in base
    assert 'id="publicNav"' in base
    assert 'id="resultados"' in home
    assert "Convierte tus datos en" in home
    assert "decisiones climáticas" in home
    assert "Plataforma digital de gestión de huella de carbono" in home
    assert "public-results-grid" in home


def test_login_keeps_official_claim_visible_on_mobile():
    login = read("login.html")
    brand_css = (STATIC / "css" / "brand-v0456.css").read_text(encoding="utf-8")
    assert "css/brand-v0456.css" in login
    assert 'class="login-mobile-claim"' in login
    assert "Convierte tus datos en decisiones climáticas." in login
    assert "@media (max-width: 900px)" in brand_css
    assert ".login-mobile-claim" in brand_css
    assert "display: block" in brand_css


def test_brand_contract_blocks_approximations_and_legacy_copy():
    manifest = json.loads((STATIC / "img" / "brand-manifest.json").read_text(encoding="utf-8"))
    assert manifest["descriptor"] == "Plataforma digital de gestión de huella de carbono"
    assert manifest["claim"] == "Convierte tus datos en decisiones climáticas"
    assert manifest["approved_master"]["redraw_allowed"] is False
    assert manifest["approved_master"]["placeholder_allowed"] is False
    assert "canonical_assets" not in manifest
    templates = "\n".join(path.read_text(encoding="utf-8") for path in TEMPLATES.glob("*.html"))
    assert "PLATAFORMA PROFESIONAL DE HUELLA DE CARBONO" not in templates
    assert "Mide. Comprende. Reduce." not in templates


def test_frontend_kit_tokens_are_canonical_and_loaded():
    tokens = json.loads((STATIC / "design-tokens.json").read_text(encoding="utf-8"))
    assert tokens["brand"] == "Calcula tu Huella"
    assert tokens["version"] == "Frontend Kit v1"
    assert tokens["colors"] == {
        "forest": "#0B3B2E",
        "forest_2": "#12533F",
        "sage": "#A7C1A0",
        "cream": "#F7F5EF",
        "slate": "#1F2933",
        "teal": "#2D6F73",
        "earth": "#CA9A6C",
        "white": "#FFFFFF",
        "line": "#DCE3DE",
        "soft_green": "#EDF4EE",
        "danger": "#C94F4F",
    }
    token_css = (STATIC / "css" / "cth-tokens.css").read_text(encoding="utf-8")
    assert "--cth-forest: #0B3B2E" in token_css
    assert "--cth-teal: #2D6F73" in token_css
    assert "--navy: var(--cth-forest)" in token_css
    for name in ("base.html", "public_base.html", "login.html", "supplier_portal.html"):
        template = read(name)
        assert "css/cth-tokens.css" in template
        assert '<meta name="theme-color" content="#0B3B2E">' in template


def test_release_is_v0455_until_visual_master_is_installed():
    config = (ROOT / "app" / "config.py").read_text(encoding="utf-8")
    assert 'version: str = "0.45.5"' in config
