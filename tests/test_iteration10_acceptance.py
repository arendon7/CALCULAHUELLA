from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from app.acceptance_certification import run_concurrent_acceptance, run_multi_organization_journeys
from app.database import Facility, Inventory, InventoryFacility, Organization, SessionLocal
from app.operations import create_backup, rehearse_backup_restore
from app.tenant_integrity import audit_chain_integrity, audit_tenant_integrity


@pytest.mark.smoke
def test_iteration10_seed_has_clean_tenant_and_audit_integrity():
    with SessionLocal() as session:
        tenant = audit_tenant_integrity(session)
        audit = audit_chain_integrity(session)
    assert tenant["ok"] is True
    assert tenant["organization_count"] >= 2
    assert tenant["checks_run"] >= 20
    assert audit["ok"] is True
    assert audit["checked"] > 0


@pytest.mark.smoke
def test_iteration10_tenant_audit_detects_cross_company_facility_link():
    with SessionLocal() as session:
        greenatics = session.scalar(select(Organization).where(Organization.trade_name == "Greenatics"))
        andinas = session.scalar(select(Organization).where(Organization.trade_name == "Industrias Andinas"))
        inventory = session.scalar(select(Inventory).where(Inventory.organization_id == greenatics.id))
        foreign_facility = session.scalar(select(Facility).where(Facility.organization_id == andinas.id))
        session.add(InventoryFacility(
            inventory_id=inventory.id,
            facility_id=foreign_facility.id,
            included=True,
            inclusion_percentage=100,
        ))
        session.flush()
        result = audit_tenant_integrity(session)
        session.rollback()
    assert result["ok"] is False
    assert any(item["code"] == "INVENTORY_FACILITY_CROSS_TENANT" for item in result["issues"])


@pytest.mark.smoke
def test_iteration10_restore_script_is_verified_and_atomic():
    root = Path(__file__).resolve().parents[1]
    source = (root / "scripts" / "restore_sqlite.py").read_text(encoding="utf-8")
    assert "extractall" not in source
    assert "verify_backup_archive" in source
    assert "rehearse_backup_restore" in source
    assert "create_backup" in source
    assert "os.replace" in source
    assert "--dry-run" in source


@pytest.mark.acceptance
@pytest.mark.integration
def test_iteration10_backup_drill_validates_tenants_and_audit_chain():
    backup = create_backup(created_by="pytest", label="iteracion-10")
    result = rehearse_backup_restore(Path(backup["path"]))
    assert result["ok"] is True, result.get("issues")
    assert result["checks"]["tenant_integrity"] is True
    assert result["checks"]["audit_chain"] is True
    assert result["tenant_integrity"]["organization_count"] >= 2


@pytest.mark.acceptance
def test_iteration10_multi_organization_journeys_are_isolated():
    result = run_multi_organization_journeys("admin@calculatuhuella.local", "Demo2026!")
    assert result["ok"] is True, result["errors"]
    assert result["organization_count"] >= 2
    assert result["membership_enforced"] is True
    assert result["request_count"] >= 18


@pytest.mark.acceptance
def test_iteration10_concurrent_local_acceptance_has_no_http_failures():
    result = run_concurrent_acceptance(
        "admin@calculatuhuella.local",
        "Demo2026!",
        workers=2,
        requests_per_worker=4,
        p95_limit_ms=10000,
    )
    assert result["ok"] is True, result["failures"]
    assert result["request_count"] == 8
    assert result["failure_count"] == 0
    with SessionLocal() as session:
        assert audit_chain_integrity(session)["ok"] is True
