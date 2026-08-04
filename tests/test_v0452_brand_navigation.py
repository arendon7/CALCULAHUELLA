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


def test_release_is_v0455_until_visual_master_is_installed():
    config = (ROOT / "app" / "config.py").read_text(encoding="utf-8")
    assert 'version: str = "0.45.5"' in config
