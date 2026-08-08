from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "app" / "templates"
STATIC = ROOT / "app" / "static"

def read(name: str) -> str:
    return (TEMPLATES / name).read_text(encoding="utf-8")

def test_canonical_brand_assets_are_present_and_used():
    for name in ("brand-primary.svg", "brand-reversed.svg", "brand-symbol.svg", "brand-manifest.json"):
        assert (STATIC / "img" / name).exists()
    combined = "\n".join(read(name) for name in ("base.html", "public_base.html", "login.html", "supplier_portal.html"))
    assert "img/brand-primary.svg" in combined
    assert "img/brand-reversed.svg" in combined
    assert "img/brand-symbol.svg" in combined

def test_public_experience_has_mobile_navigation_and_clear_results():
    base = read("public_base.html")
    home = read("public_home.html")
    reports = read("public/v14/reports_decision.html")
    assert "data-menu-button" in base
    assert 'aria-controls="mobilePanel"' in base
    assert 'id="mobilePanel"' in base
    assert "data-mobile-panel" in base
    assert 'public/v14/reports_decision.html' in home
    assert 'id="informes"' in reports
    assert "Un mismo inventario, diferentes formas de comunicarlo" in reports
    assert "La medición es el punto de partida" in reports

def test_release_is_v0453():
    config = (ROOT / "app" / "config.py").read_text(encoding="utf-8")
    assert 'version: str = "1.0.0"' in config
