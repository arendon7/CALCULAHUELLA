from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.automations import AUTOMATION_TYPES
from app.config import settings
from app.database import Base, ENGINE, init_db
from app.main import app
from app.operations import create_backup, verify_backup_archive
from app.production_readiness import production_profile, sanitized_environment_template


@pytest.fixture(autouse=True)
def fresh_database():
    # La base semilla aislada se restaura desde tests/conftest.py.
    yield


def login(client: TestClient, email: str = "admin@calculatuhuella.local") -> None:
    response = client.post("/login", data={"email": email, "password": "Demo2026!"}, follow_redirects=False)
    assert response.status_code == 303


def test_v100final_operations_map_and_sanitized_template():
    with TestClient(app) as client:
        login(client)
        page = client.get("/operacion")
        assert page.status_code == 200
        assert "MAPA PRODUCTIVO" in page.text
        assert "PostgreSQL" in page.text
        template = client.get("/operacion/configuracion/plantilla")
        assert template.status_code == 200
        assert "BACKUP_SIGNING_SECRET" in template.text
        assert settings.session_secret not in template.text


def test_v100final_production_api_exposes_seven_layers():
    with TestClient(app) as client:
        login(client)
        response = client.get("/api/operacion/preparacion")
        assert response.status_code == 200
        profile = response.json()["production_profile"]
        assert profile["version"] == "1.0.0"
        assert profile["total_stages"] == 7
        assert {stage["code"] for stage in profile["stages"]} == {
            "runtime", "database", "storage", "communications", "continuity", "security", "observability"
        }


def test_v100final_backup_v2_is_signed_and_payloads_are_verified():
    original_secret = settings.backup_signing_secret
    original_offsite = settings.backup_offsite_enabled
    try:
        object.__setattr__(settings, "backup_signing_secret", "s" * 48)
        object.__setattr__(settings, "backup_offsite_enabled", False)
        result = create_backup(created_by="pytest", label="signed")
        checked = verify_backup_archive(Path(result["path"]))
        assert result["signed"] is True
        assert checked["ok"] is True
        assert checked["signature_valid"] is True
        assert checked["payloads_checked"] >= 2
        with zipfile.ZipFile(result["path"]) as archive:
            manifest = json.loads(archive.read("manifest.json"))
        assert manifest["backup_format_version"] == 2
        assert manifest["signature_algorithm"] == "HMAC-SHA256"
        assert manifest["payloads"]
    finally:
        object.__setattr__(settings, "backup_signing_secret", original_secret)
        object.__setattr__(settings, "backup_offsite_enabled", original_offsite)


def test_v100final_backup_replication_uses_separate_prefix():
    original_secret = settings.backup_signing_secret
    original_offsite = settings.backup_offsite_enabled
    original_prefix = settings.backup_storage_prefix
    try:
        object.__setattr__(settings, "backup_signing_secret", "r" * 48)
        object.__setattr__(settings, "backup_offsite_enabled", True)
        object.__setattr__(settings, "backup_storage_prefix", "offsite-test")
        result = create_backup(created_by="pytest", label="offsite")
        assert result["offsite_key"].startswith("offsite-test/")
        from app.storage import storage
        assert storage.exists(result["offsite_key"])
    finally:
        object.__setattr__(settings, "backup_signing_secret", original_secret)
        object.__setattr__(settings, "backup_offsite_enabled", original_offsite)
        object.__setattr__(settings, "backup_storage_prefix", original_prefix)


def test_v100final_sanitized_template_never_reuses_runtime_secrets(tmp_path: Path):
    payload = sanitized_environment_template()
    assert "GENERAR_SECRETO" in payload
    assert settings.session_secret not in payload
    assert "DATABASE_URL=postgresql+psycopg" in payload
    assert "OBJECT_STORAGE_VERSIONING_CONFIRMED=true" in payload

    root = Path(__file__).resolve().parents[1]
    destination = tmp_path / ".env.production.template"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root)
    result = subprocess.run(
        [sys.executable, str(root / "scripts/generate_production_env.py"), str(destination)],
        cwd=root, env=env, capture_output=True, text=True, timeout=30, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    generated = destination.read_text(encoding="utf-8")
    assert generated == payload
    assert settings.session_secret not in generated


def test_v100final_scheduled_backup_and_production_stack_are_registered():
    assert "Respaldo programado" in AUTOMATION_TYPES
    root = Path(__file__).resolve().parents[1]
    compose = (root / "docker-compose.production.yml").read_text(encoding="utf-8")
    for service in ("postgres:", "minio:", "worker:", "prometheus:", "alertmanager:", "grafana:", "caddy:"):
        assert service in compose
    assert (root / "deployment/prometheus-alerts.yml").is_file()
    assert (root / "scripts/run_production_audit.py").is_file()


def test_v100final_client_cannot_access_operations_or_template():
    with TestClient(app) as client:
        login(client, "cliente@calculatuhuella.local")
        assert client.get("/operacion").status_code == 403
        assert client.get("/operacion/configuracion/plantilla").status_code == 403
