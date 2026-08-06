from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_iteration_1_repairs_broken_methodology_link() -> None:
    text = (ROOT / "app/experience_web.py").read_text(encoding="utf-8")
    assert '"href": "/metodologia/cierre"' in text
    assert '"href": "/metodologia-cierre"' not in text


def test_iteration_1_encodes_guided_capture_query_separator() -> None:
    text = (ROOT / "app/templates/guided_capture.html").read_text(encoding="utf-8")
    assert "&amp;copy_record_id=" in text
    assert "&copy_record_id=" not in text


def test_iteration_1_hides_unauthorized_portfolio_link() -> None:
    text = (ROOT / "app/templates/base.html").read_text(encoding="utf-8")
    assert "user.can_manage_portfolio" in text
    assert 'title="Organización activa"' in text


def test_iteration_1_respects_locked_inventory_state() -> None:
    inventory = (ROOT / "app/templates/inventory.html").read_text(encoding="utf-8")
    inventories = (ROOT / "app/templates/inventories.html").read_text(encoding="utf-8")
    readiness = (ROOT / "app/delivery_readiness.py").read_text(encoding="utf-8")
    assert "user.can_manage_inventory and not inventory.locked" in inventory
    assert "user.can_manage_inventory and not inventory.locked" in inventories
    assert '"/control" if inventory.locked' in readiness
