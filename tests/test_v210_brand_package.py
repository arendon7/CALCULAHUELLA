from pathlib import Path

import pytest

pytestmark = pytest.mark.smoke
ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "app" / "templates"
MAKEFILE = ROOT / "Makefile"
PUBLIC_CSS = ROOT / "app" / "static" / "css" / "public-v1.6.css"


def all_templates() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(TEMPLATES.rglob("*.html"))
    )


def test_only_two_canonical_brand_assets_are_active_in_templates():
    combined = all_templates()
    assert "img/brand-primary.svg" in combined
    assert "img/brand-symbol.svg" in combined
    for forbidden in (
        "brand-reversed.svg",
        "logo.svg",
        "logo-white.svg",
        "favicon.svg",
        "logo-oficial.png",
        "logo-oficial-blanco.png",
        "favicon-64.png",
        "favicon-256.png",
    ):
        assert forbidden not in combined


def test_public_header_footer_and_favicon_share_exact_canonical_assets():
    public_base = (TEMPLATES / "public_base.html").read_text(encoding="utf-8")
    assert public_base.count("img/brand-primary.svg") >= 2
    assert "img/brand-symbol.svg" in public_base
    assert "canonical-footer-logo" in public_base

    css = PUBLIC_CSS.read_text(encoding="utf-8")
    assert ".canonical-footer-logo" in css
    assert "background:#fff" in css
    assert "filter:" not in css.split(".canonical-footer-logo", 1)[1].split("\n", 1)[0]


def test_superseded_png_recovery_tooling_is_removed():
    for relative in (
        "scripts/brand/extract_embedded_master.py",
        "scripts/brand/audit_historical_sources.py",
        "scripts/brand/import_master_package.py",
    ):
        assert not (ROOT / relative).exists(), relative


def test_makefile_exposes_only_strict_canonical_brand_gate():
    source = MAKEFILE.read_text(encoding="utf-8")
    assert "brand-check:" in source
    assert "brand-require-canonical:" in source
    assert "--require-canonical" in source
    for obsolete in (
        "brand-audit-history:",
        "brand-recover-primary:",
        "brand-validate-package:",
        "brand-install-master:",
    ):
        assert obsolete not in source
