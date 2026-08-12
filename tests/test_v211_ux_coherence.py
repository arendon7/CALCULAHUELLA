from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_BASE = ROOT / "app" / "templates" / "public_base.html"
HERO = ROOT / "app" / "templates" / "public" / "v14" / "hero_trust.html"
REPORTS = ROOT / "app" / "templates" / "public" / "v14" / "reports_decision.html"
PUBLIC_CSS = ROOT / "app" / "static" / "css" / "v2.1-public.css"
PRODUCT_CSS = ROOT / "app" / "static" / "css" / "v2.1-ui.css"
APP_CSS = ROOT / "app" / "static" / "css" / "app.css"


@pytest.mark.smoke
def test_public_information_architecture_has_one_home_anchor_and_four_primary_destinations() -> None:
    base = PUBLIC_BASE.read_text(encoding="utf-8")
    hero = HERO.read_text(encoding="utf-8")

    assert (base + hero).count('id="inicio"') == 1

    nav = base.split('<nav class="nav-links"', 1)[1].split("</nav>", 1)[0]
    assert nav.count("<a ") == 4
    for target in ("/#como-funciona", "/#plataforma", "/#informes", "/#soluciones"):
        assert target in nav
    assert "/#experiencia" not in nav
    assert "/#recursos" not in nav


@pytest.mark.smoke
def test_hero_keeps_one_primary_journey_and_demo_as_tertiary_access() -> None:
    hero = HERO.read_text(encoding="utf-8")
    actions = hero.split('<div class="hero-actions">', 1)[1].split("</div>", 1)[0]

    assert actions.count("<a ") == 2
    assert 'href="/diagnostico"' in actions
    assert 'href="#como-funciona"' in actions
    assert "Abrir demo funcional" not in actions
    assert 'class="hero-demo-link" href="/login"' in hero


@pytest.mark.smoke
def test_public_product_mockup_uses_the_exact_canonical_symbol() -> None:
    hero = HERO.read_text(encoding="utf-8")
    assert 'class="app-logo-mini"' in hero
    assert "img/brand-symbol.svg" in hero
    assert ">CTH<" not in hero


@pytest.mark.smoke
def test_public_report_preview_uses_exact_canonical_brand_surface() -> None:
    reports = REPORTS.read_text(encoding="utf-8")
    assert "logo-master.svg" not in reports
    assert "img/brand-primary.svg" in reports


@pytest.mark.smoke
def test_coherence_layers_are_loaded_and_preserve_accessible_motion_and_focus() -> None:
    base = PUBLIC_BASE.read_text(encoding="utf-8")
    app_css = APP_CSS.read_text(encoding="utf-8")
    public_css = PUBLIC_CSS.read_text(encoding="utf-8")
    product_css = PRODUCT_CSS.read_text(encoding="utf-8")

    assert "css/v2.1-public.css" in base
    assert 'url("./v2.1-ui.css")' in app_css
    for css in (public_css, product_css):
        assert "prefers-reduced-motion:reduce" in css
        assert ":focus-visible" in css

    # The V2.1 layer is intentionally namespaced to the public shell; the
    # contract protects the 4x2 desktop layout without encouraging global CSS.
    assert ".public-v14-body .process-nav{grid-template-columns:repeat(4,minmax(0,1fr))}" in public_css
    assert "body.app-shell" in product_css
    assert ".work-center-head .head-actions .btn{display:none}" in product_css


@pytest.mark.smoke
def test_v212_mobile_and_brand_polish_are_fail_closed() -> None:
    public_css = PUBLIC_CSS.read_text(encoding="utf-8")
    product_css = PRODUCT_CSS.read_text(encoding="utf-8")

    # Public pages avoid horizontal masking and collapse dense visual systems
    # intentionally instead of hiding overflow defects.
    assert "overflow-x:clip" in public_css
    assert "overflow-x:hidden" not in public_css
    assert "@media(max-width:620px)" in public_css
    assert ".product-stage .app-side{display:none}" in public_css

    # The authenticated shell must render the canonical coloured logo as-is,
    # not visually manufacture an unapproved white/reversed variant.
    assert ".sidebar .brand img{filter:none" in product_css

    # Mobile product UI keeps task navigation reachable above device safe areas.
    assert "env(safe-area-inset-bottom)" in product_css
    assert ".mobile-taskbar" in product_css
    assert "min-height:54px" in product_css

    # The dashboard remains task-first and collapses density deliberately.
    assert ".inventory-pulse{display:grid" in product_css
    assert "@media(max-width:900px)" in product_css
    assert ".workspace-steps{grid-template-columns:1fr}" in product_css
