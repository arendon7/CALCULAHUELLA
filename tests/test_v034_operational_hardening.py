from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select

from app.database import Base, ENGINE, RestoreDrill, SessionLocal, init_db
from app.main import app
from app.operations import create_backup, diagnostic_snapshot, rehearse_backup_restore


@pytest.fixture(autouse=True)
def fresh_database_v034():
    # La base semilla aislada se restaura desde tests/conftest.py.
    yield


def login_admin(client: TestClient) -> None:
    response = client.post(
        "/login",
        data={"email": "admin@calculatuhuella.local", "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v034_health_schema_and_inventory_version_are_current():
    with TestClient(app) as client:
        assert client.get("/api/health").json()["version"] == "1.0.0"
    assert "restore_drills" in inspect(ENGINE).get_table_names()
    with SessionLocal() as session:
        versions = {item.version for item in session.execute(select(__import__('app.database', fromlist=['Inventory']).Inventory)).scalars()}
        assert "0.45" in versions
        assert "0.33" not in versions


def test_v034_backup_can_be_restored_and_validated_in_isolation():
    backup = create_backup(created_by="test", label="restore-drill")
    result = rehearse_backup_restore(Path(backup["path"]))
    assert result["ok"] is True
    assert result["status"] == "Aprobado"
    assert result["integrity_result"].lower() == "ok"
    assert result["table_count"] >= 8
    assert result["record_summary"]["organizations"] >= 1
    assert result["checks"]["required_tables"] is True


def test_v034_corrupt_backup_is_rejected_without_touching_live_database(tmp_path: Path):
    path = tmp_path / "corrupt.zip"
    path.write_bytes(b"not-a-zip")
    result = rehearse_backup_restore(path)
    assert result["ok"] is False
    assert result["status"] == "Fallido"
    with SessionLocal() as session:
        assert session.scalar(select(__import__('app.database', fromlist=['Organization']).Organization)) is not None


def test_v034_web_rehearsal_persists_evidence_and_audit_record():
    backup = create_backup(created_by="test", label="web-drill")
    name = Path(backup["path"]).name
    with TestClient(app) as client:
        login_admin(client)
        page = client.get("/operacion")
        assert page.status_code == 200
        assert "Ensayar restauración" in page.text
        response = client.post(f"/operacion/respaldos/{name}/ensayar", data={"notes": "Prueba controlada"}, follow_redirects=False)
        assert response.status_code == 303
    with SessionLocal() as session:
        drill = session.scalar(select(RestoreDrill).where(RestoreDrill.backup_name == name))
        assert drill is not None
        assert drill.status == "Aprobado"
        assert drill.integrity_result.lower() == "ok"
        assert drill.performed_by == "admin@calculatuhuella.local"
        assert drill.completed_at is not None


def test_v034_operations_are_registered_outside_main_controller():
    import app.main as main_module
    import app.operations_web as operations_web

    main_source = Path(main_module.__file__).read_text(encoding="utf-8")
    operations_source = Path(operations_web.__file__).read_text(encoding="utf-8")
    assert 'register_operations_routes(' in main_source
    assert '@app.get("/operacion"' not in main_source
    assert '"/operacion"' in operations_source
    assert len(main_source.splitlines()) < 5950


def test_v034_diagnostic_reports_restore_continuity_state():
    before = diagnostic_snapshot()
    assert before["restore_drill"]["ok"] is False
    backup = create_backup(created_by="test", label="diagnostic")
    result = rehearse_backup_restore(Path(backup["path"]))
    with SessionLocal() as session:
        session.add(RestoreDrill(
            organization_id=1,
            backup_name=Path(backup["path"]).name,
            backup_sha256=str(result["backup_sha256"]),
            application_version=str(result["application_version"]),
            database_backend=str(result["database_backend"]),
            status="Aprobado",
            integrity_result="ok",
            table_count=int(result["table_count"]),
            performed_by="test",
        ))
        session.commit()
    after = diagnostic_snapshot()
    assert after["restore_drill"]["ok"] is True
    assert after["restore_drill"]["status"] == "Vigente"
