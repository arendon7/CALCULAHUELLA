from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "app" / "templates"

def read(name: str) -> str:
    return (TEMPLATES / name).read_text(encoding="utf-8")

def test_primary_surfaces_use_user_facing_language():
    public = read("public_home.html")
    hero = read("public/v14/hero_trust.html")
    login = read("login.html")
    dashboard = read("dashboard.html")
    source = read("source.html")
    assert 'public/v14/hero_trust.html' in public
    assert 'public/v14/experience_resources_cta.html' in public
    assert "Toda tu gestión de carbono" in hero
    assert "Plataforma colaborativa de gestión de carbono" in hero
    assert "V0.45" not in login
    assert "V0.45" not in dashboard
    assert "<span>V0.4</span>" not in source

def test_topbar_routes_to_current_delivery_control():
    base = read("base.html")
    assert 'href="/entrega-profesional"' in base
    assert '<span>Inventario</span>' in base
    assert 'aria-label="Estado del inventario:' in base
    navigation = (ROOT / "app" / "product_experience.py").read_text(encoding="utf-8")
    assert '"Perfil y diagnóstico", "/inteligencia-producto"' in navigation

def test_application_release_is_v0453():
    config = (ROOT / "app" / "config.py").read_text(encoding="utf-8")
    assert 'version: str = "1.0.0"' in config
