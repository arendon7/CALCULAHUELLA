from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "app" / "templates"

def read(name: str) -> str:
    return (TEMPLATES / name).read_text(encoding="utf-8")

def test_primary_surfaces_use_user_facing_language():
    public = read("public_home.html")
    login = read("login.html")
    dashboard = read("dashboard.html")
    source = read("source.html")
    assert "Gestión de Carbono" in public
    assert "Gestión Avanzada y Verificación" in public
    assert "public-audience-strip" in public
    assert "V0.45" not in login
    assert "V0.45" not in dashboard
    assert "<span>V0.4</span>" not in source

def test_topbar_routes_profile_and_scope():
    assert 'href="/inteligencia-producto">Perfil y alcance' in read("base.html")

def test_application_release_is_v0453():
    config = (ROOT / "app" / "config.py").read_text(encoding="utf-8")
    assert 'version: str = "0.45.5"' in config
