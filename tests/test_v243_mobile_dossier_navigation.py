from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOSSIER_CSS = ROOT / "app" / "static" / "css" / "inventory-dossier.css"
BASE_TEMPLATE = ROOT / "app" / "templates" / "base.html"


def test_v243_dossier_override_loads_after_base_css() -> None:
    template = BASE_TEMPLATE.read_text(encoding="utf-8")
    assert template.index("css/app.css") < template.index("css/inventory-dossier.css")


def test_v243_mobile_dossier_uses_visible_grid_instead_of_horizontal_carousel() -> None:
    css = DOSSIER_CSS.read_text(encoding="utf-8")
    mobile = css.split("/* V2.43", 1)[1]

    assert "@media(max-width:720px)" in mobile
    assert "grid-template-columns:repeat(3,minmax(0,1fr))" in mobile
    assert "grid-auto-flow:unset" in mobile
    assert "overflow-x:visible" in mobile
    assert "scroll-snap-type:none" in mobile
    assert "min-height:58px" in mobile
    assert "body.app-shell .inventory-dossier-nav>a>small" in mobile
    assert "display:none" in mobile
    assert "grid-auto-flow:column" not in mobile
    assert "overflow-x:auto" not in mobile


def test_v243_template_keeps_all_seven_scoped_dossier_views() -> None:
    template = BASE_TEMPLATE.read_text(encoding="utf-8")
    expected_fragments = [
        "'label': 'Ficha'",
        "'label': 'Datos'",
        "'label': 'Resultados'",
        "'label': 'Análisis'",
        "'label': 'Reducción'",
        "'label': 'Informes'",
        "'label': 'Cierre'",
        "dossier_root ~ '/informacion'",
        "dossier_root ~ '/calculos'",
        "dossier_root ~ '/analisis'",
        "dossier_root ~ '/reduccion'",
        "dossier_root ~ '/reportes'",
        "dossier_root ~ '/entrega-profesional'",
    ]
    for fragment in expected_fragments:
        assert fragment in template
    assert "data-inventory-dossier-nav" in template
    assert "aria-current=\"page\"" in template
