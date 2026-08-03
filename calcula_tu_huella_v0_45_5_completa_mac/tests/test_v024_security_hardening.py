from io import BytesIO
from pathlib import Path
import zipfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import AuditEvent, Base, ENGINE, SessionLocal, add_audit, init_db
from app.main import app
from app.operations import create_backup, verify_audit_integrity, verify_backup_archive
from app.security import login_throttle, validate_upload_bytes


@pytest.fixture(autouse=True)
def fresh_database_v024():
    Base.metadata.drop_all(ENGINE)
    init_db()
    yield


def test_v024_health_and_request_id():
    with TestClient(app) as client:
        response = client.get("/api/health", headers={"X-Request-ID": "test-request-024"})
        assert response.status_code == 200
        assert response.json()["version"] == "0.45.5"
        assert response.headers["x-request-id"] == "test-request-024"


def test_v024_csrf_cookie_is_issued():
    with TestClient(app) as client:
        response = client.get("/login")
        assert response.status_code == 200
        assert client.cookies.get("cth_csrf")
        assert "_csrf_token" in response.text or "app.js" in response.text


def test_v024_persistent_login_throttle_survives_instances():
    email = "seguridad@example.test"
    ip = "198.51.100.9"
    login_throttle.success(email, ip)
    for _ in range(4):
        assert login_throttle.failure(email, ip).blocked is False
    blocked = login_throttle.failure(email, ip)
    assert blocked.blocked is True
    assert login_throttle.status(email, ip).blocked is True
    login_throttle.success(email, ip)
    assert login_throttle.status(email, ip).blocked is False


def test_v024_audit_chain_detects_tampering():
    with SessionLocal() as session:
        add_audit(session, 1, "admin@test", "CREAR", "Prueba", "Uno", detail="Primero")
        add_audit(session, 1, "admin@test", "EDITAR", "Prueba", "Dos", detail="Segundo")
        session.commit()
    result = verify_audit_integrity()
    assert result["ok"] is True
    assert result["checked"] >= 2

    with SessionLocal() as session:
        event = session.scalar(select(AuditEvent).where(AuditEvent.action == "EDITAR"))
        event.detail = "Manipulado"
        session.commit()
    result = verify_audit_integrity()
    assert result["ok"] is False
    assert result["failure_count"] >= 1
    init_db()  # Reiniciar no debe "reparar" una manipulación.
    assert verify_audit_integrity()["ok"] is False


def test_v024_upload_signature_validation():
    ok, _, mime = validate_upload_bytes("evidencia.pdf", b"%PDF-1.7\ncontenido", "application/pdf", {".pdf"})
    assert ok is True and mime == "application/pdf"
    ok, message, _ = validate_upload_bytes("evidencia.pdf", b"MZnot-a-pdf", "application/pdf", {".pdf"})
    assert ok is False and "ejecutable" in message

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("xl/workbook.xml", "<workbook />")
    ok, _, mime = validate_upload_bytes(
        "datos.xlsx",
        buffer.getvalue(),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        {".xlsx"},
    )
    assert ok is True and "spreadsheet" in mime


def test_v024_backup_integrity_verification():
    result = create_backup(created_by="prueba", label="seguridad")
    verified = verify_backup_archive(Path(result["path"]))
    assert verified["ok"] is True
    assert verified["sha256"] == result["sha256"]
    assert verified["members"] >= 2


def test_v024_operations_dashboard_shows_security_controls():
    with TestClient(app) as client:
        login = client.post(
            "/login",
            data={"email": "admin@calculatuhuella.local", "password": "Demo2026!"},
            follow_redirects=False,
        )
        assert login.status_code == 303
        response = client.get("/operacion")
        assert response.status_code == 200
        assert "Protección CSRF" in response.text
        assert "Cadena de auditoría" in response.text
        assert "Registro estructurado" in response.text
