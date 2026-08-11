from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace

from app.capture_guidance import capture_summary, is_activity_capture_source


ROOT = Path(__file__).resolve().parents[1]


def _source(*, name: str, category: str, records: list[object] | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        name=name,
        category=category,
        included=True,
        data_frequency="Anual",
        activity_records=records or [],
        materiality="Alta",
        scope=3,
        preferred_unit="tCO₂e",
    )


def test_supplier_consolidation_is_not_an_activity_capture_source() -> None:
    supplier = _source(
        name="Cadena de valor consolidada desde proveedores",
        category="Datos específicos de proveedores",
    )
    assert is_activity_capture_source(supplier) is False

    inventory = SimpleNamespace(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        sources=[supplier],
    )
    summary = capture_summary(inventory)
    assert summary["sources"] == 0
    assert summary["cards"] == []
    assert summary["expected_periods"] == 0


def test_operational_source_remains_in_guided_capture() -> None:
    operational = _source(name="Transporte contratado", category="Transporte y distribución")
    assert is_activity_capture_source(operational) is True

    inventory = SimpleNamespace(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        sources=[operational],
    )
    summary = capture_summary(inventory)
    assert summary["sources"] == 1
    assert summary["cards"][0]["source"] is operational
    assert summary["cards"][0]["next_start"] == date(2025, 1, 1)


def test_direct_capture_endpoint_rejects_supplier_managed_source() -> None:
    source = (ROOT / "app" / "capture_web.py").read_text(encoding="utf-8")
    assert "if not is_activity_capture_source(source):" in source
    assert 'raise HTTPException(409, "Esta fuente se gestiona desde Cadena de valor' in source
