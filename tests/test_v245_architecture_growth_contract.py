from __future__ import annotations

from pathlib import Path

from scripts.audit_architecture import APPROVED_GROWTH, BASELINE, approved_limit


ROOT = Path(__file__).resolve().parents[1]
ADR = ROOT / "docs" / "architecture" / "ADR-002-explicit-inventory-scoped-workspace.md"


def test_v245_route_growth_is_specific_and_baseline_remains_immutable() -> None:
    assert BASELINE["total_routes"] == 344
    approval = APPROVED_GROWTH["total_routes"]
    assert approval["allowance"] == 6
    assert approved_limit("total_routes", BASELINE["total_routes"]) == 350
    assert "ADR-002" in approval["reason"]
    assert "V2.45" in approval["reason"]
    assert "read-only source trace" in approval["reason"]


def test_v245_adr_explicitly_authorizes_only_scoped_source_trace_growth() -> None:
    text = ADR.read_text(encoding="utf-8")

    assert "/inventarios/{id}/fuentes/{source_id}" in text
    assert "una ruta adicional V2.45" in text
    assert "GET-only" in text
    assert "+6 rutas sobre el baseline de 344" in text
    assert "límite total de **350**" in text
    assert "no** habilita crecimiento genérico" in text
    assert "source.inventory_id == inventory_id" in text
    assert "No se crea un segundo motor de cálculo" in text
