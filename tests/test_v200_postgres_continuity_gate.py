from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "postgres_restore_gate.py"
WORKFLOW = ROOT / ".github" / "workflows" / "iteration4-stabilization.yml"


def test_v200_postgres_restore_gate_is_conservative_and_isolated() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "POSTGRES_RESTORE_DATABASE_URL" in source
    assert "create_backup" in source
    assert "verify_backup_archive" in source
    assert 'archive_check.get("signature_valid") is True' in source
    assert "pg_restore" in source
    assert "RESTORE_REQUIRED_TABLES" in source
    assert "source_counts == target_counts" in source
    assert "audit_tenant_integrity(session)" in source
    assert "audit_chain_integrity(session)" in source
    assert 'result["ok"] = all(checks.values()) and not issues' in source


def test_v200_product_readiness_workflow_has_real_postgres_restore_job() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")
    assert "postgres-continuity:" in source
    assert "postgres:16" in source
    assert "requirements-prod.txt" in source
    assert "postgresql-client" in source
    assert "calculahuella_source" in source
    assert "calculahuella_restore" in source
    assert "BACKUP_SIGNING_SECRET" in source
    assert "POSTGRES_RESTORE_DATABASE_URL" in source
    assert "python scripts/postgres_restore_gate.py" in source
    assert "postgres-restore-evidence.json" in source
    assert "postgres-continuity-evidence" in source


def test_v200_postgres_continuity_is_part_of_targeted_release_contract() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")
    assert "tests/test_v200_postgres_continuity_gate.py" in source
