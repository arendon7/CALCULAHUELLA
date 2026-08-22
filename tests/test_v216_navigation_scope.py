from __future__ import annotations

from pathlib import Path

import pytest

from app.product_experience import navigation_for

ROOT = Path(__file__).resolve().parents[1]
PERIOD_CLOSE = ROOT / "app" / "templates" / "period_close.html"


@pytest.mark.smoke
def test_monthly_close_is_scoped_once_to_greenatics_pilot() -> None:
    navigation = navigation_for(
        {
            "role": "Consultor",
            "capabilities": {
                "provide_data",
                "manage_sources",
                "review",
                "approve",
                "view_methodology",
            },
        },
        "complete",
    )

    hits = [
        (section["label"], item["label"])
        for group in ("core", "advanced", "internal")
        for section in navigation[group]
        for item in section["items"]
        if item["href"] == "/cierre-mensual"
    ]

    assert hits == [("PILOTO GREENATICS", "Cierre mensual del piloto")]


@pytest.mark.smoke
def test_monthly_close_page_identifies_the_pilot_context() -> None:
    template = PERIOD_CLOSE.read_text(encoding="utf-8")

    assert "Piloto Greenatics / Cierre mensual" in template
    assert "PILOTO GREENATICS · CONCILIACIÓN Y CIERRE DEL PERIODO" in template
    assert "Cierre mensual del piloto" in template
    assert "datos, evidencia, factores y cálculos del piloto" in template
