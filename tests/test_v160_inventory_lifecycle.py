from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

import app.inventory_lifecycle as lifecycle
import app.main as main_module
from app.db.base import SessionLocal
from app.db.models import Inventory, ReviewObservation
from app.inventory_context import get_inventory

ROOT = Path(__file__).resolve().parents[1]


def test_v160_inventory_lifecycle_has_dedicated_authority_and_compatible_imports():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    lifecycle_source = (ROOT / "app/inventory_lifecycle.py").read_text(encoding="utf-8")
    assert "def next_inventory_version(" not in main_source
    assert "def clone_inventory_version(" not in main_source
    assert "def next_inventory_version(" in lifecycle_source
    assert "def clone_inventory_version(" in lifecycle_source
    assert "from .main import" not in lifecycle_source
    assert main_module.next_inventory_version is lifecycle.next_inventory_version
    assert main_module.clone_inventory_version is lifecycle.clone_inventory_version


def test_v160_next_inventory_version_preserves_historical_contract():
    assert lifecycle.next_inventory_version("") == "1.0-r1"
    assert lifecycle.next_inventory_version("1.0") == "1.0-r1"
    assert lifecycle.next_inventory_version("1.0-r1") == "1.0-r2"
    assert lifecycle.next_inventory_version("v2026-r9") == "v2026-r10"


def test_v160_clone_inventory_version_preserves_structure_and_original():
    with SessionLocal() as session:
        original_stub = session.scalar(select(Inventory).order_by(Inventory.id))
        assert original_stub is not None
        original = get_inventory(
            session, {"organization_id": original_stub.organization_id}, original_stub.id
        )
        original_status = original.status
        original_locked = original.locked
        original_version = original.version
        source_count = len(original.sources)
        facility_count = len(original.facility_links)
        action_count = len(original.reduction_actions)
        target_count = len(original.targets)

        user = {
            "email": "admin@calculatuhuella.local",
            "name": "Administrador Demo",
        }
        cloned = lifecycle.clone_inventory_version(session, original, user, "Corrección controlada V1.6")
        session.flush()

        assert cloned.id != original.id
        assert cloned.organization_id == original.organization_id
        assert cloned.parent_inventory_id == original.id
        assert cloned.version == lifecycle.next_inventory_version(original_version)
        assert cloned.status == "Borrador"
        assert cloned.current_stage == "Corrección"
        assert cloned.locked is False
        assert len(cloned.sources) == source_count
        assert len(cloned.facility_links) == facility_count
        assert len(cloned.reduction_actions) == action_count
        assert len(cloned.targets) == target_count
        observation = session.scalar(
            select(ReviewObservation).where(ReviewObservation.inventory_id == cloned.id)
        )
        assert observation is not None
        assert observation.severity == "Mayor"
        assert "Corrección controlada V1.6" in observation.description

        assert original.status == original_status
        assert original.locked == original_locked
        assert original.version == original_version
        session.rollback()


def test_v160_review_surface_receives_extracted_lifecycle_service():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    assert "review_gate_summary, clone_inventory_version," in main_source
    assert "from .inventory_lifecycle import clone_inventory_version, next_inventory_version" in main_source
