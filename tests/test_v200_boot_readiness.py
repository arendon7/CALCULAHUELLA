from __future__ import annotations

import io
from dataclasses import replace
from pathlib import Path

import boto3
from fastapi.testclient import TestClient

import app.storage as storage_module
from app.production_readiness import sanitized_environment_template


ROOT = Path(__file__).resolve().parents[1]


class _FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    def put_object(self, *, Bucket, Key, Body, ContentType=None):
        self.objects[(Bucket, Key)] = bytes(Body)

    def get_object(self, *, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)])}

    def delete_object(self, *, Bucket, Key):
        self.objects.pop((Bucket, Key), None)

    def head_object(self, *, Bucket, Key):
        if (Bucket, Key) not in self.objects:
            raise KeyError(Key)
        return {}

    def list_objects_v2(self, **kwargs):
        return {"Contents": [], "IsTruncated": False}

    def upload_file(self, *args, **kwargs):
        return None

    def generate_presigned_url(self, *args, **kwargs):
        return "https://example.invalid/signed"


def test_v200_startup_binds_before_external_storage_readiness() -> None:
    start = (ROOT / "start_prod.sh").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    ready_script = (ROOT / "scripts" / "check_ready.py").read_text(encoding="utf-8")

    assert '"$PY" -m alembic upgrade head' in start
    assert 'exec "$PY" -m uvicorn app.main:app' in start
    assert '"$PY" scripts/check_ready.py' not in start
    assert "/api/health" in dockerfile
    assert "diagnostic_snapshot()" in ready_script
    assert 'return 0 if snapshot.get("status") == "ready" else 1' in ready_script


def test_v200_s3_probe_is_fail_fast_and_does_not_replace_operational_client(monkeypatch) -> None:
    original = storage_module.settings
    calls: list[dict[str, object]] = []

    def fake_client(service_name: str, **kwargs):
        assert service_name == "s3"
        calls.append(kwargs)
        return _FakeS3Client()

    monkeypatch.setattr(boto3, "client", fake_client)
    s3_settings = replace(
        original,
        storage_backend="s3",
        s3_bucket="bucket-test",
        s3_endpoint_url="https://s3.example.invalid",
        s3_access_key="key",
        s3_secret_key="secret",
        s3_connect_timeout_seconds=5.0,
        s3_read_timeout_seconds=30.0,
        s3_max_attempts=3,
        external_probe_timeout_seconds=0.75,
    )
    monkeypatch.setattr(storage_module, "settings", s3_settings)

    service = storage_module.StorageService()
    assert calls == []
    assert service._client is None

    probe = service.verified_probe()
    assert probe["ok"] is True
    assert service._client is None
    assert len(calls) == 1
    probe_config = calls[0]["config"]
    assert probe_config.connect_timeout == 0.75
    assert probe_config.read_timeout == 0.75
    assert probe_config.retries["total_max_attempts"] == 1

    service.put_bytes("demo/a.txt", b"abc", "text/plain")
    assert len(calls) == 2
    normal_config = calls[1]["config"]
    assert normal_config.connect_timeout == 5.0
    assert normal_config.read_timeout == 30.0
    assert normal_config.retries["total_max_attempts"] == 3
    cached = service._client
    service.exists("demo/a.txt")
    assert service._client is cached
    assert len(calls) == 2


def test_v200_invalid_custom_s3_configuration_degrades_before_network(monkeypatch) -> None:
    original = storage_module.settings
    calls: list[dict[str, object]] = []

    def fake_client(service_name: str, **kwargs):
        calls.append(kwargs)
        return _FakeS3Client()

    monkeypatch.setattr(boto3, "client", fake_client)
    invalid = replace(
        original,
        storage_backend="s3",
        s3_bucket="bucket-test",
        s3_endpoint_url="https://s3.example.invalid",
        s3_access_key="",
        s3_secret_key="",
    )
    monkeypatch.setattr(storage_module, "settings", invalid)

    result = storage_module.StorageService().verified_probe()
    assert result["ok"] is False
    assert "obligatorios" in result["detail"]
    assert calls == []
    assert any("endpoints S3 personalizados" in item for item in invalid.production_issues())


def test_v200_filesystem_storage_is_lazy_until_first_operation(monkeypatch, tmp_path) -> None:
    target = tmp_path / "mount" / "documents"
    settings = replace(
        storage_module.settings,
        storage_backend="filesystem",
        external_storage_root=str(target),
    )
    monkeypatch.setattr(storage_module, "settings", settings)

    service = storage_module.StorageService()
    assert not target.exists()
    service.put_bytes("proof.txt", b"ok")
    assert target.joinpath("proof.txt").read_bytes() == b"ok"


def test_v200_ready_remains_strict_when_storage_is_degraded(monkeypatch) -> None:
    import app.main as main_module

    client = TestClient(main_module.app)
    monkeypatch.setattr(
        main_module,
        "diagnostic_snapshot",
        lambda: {
            "status": "degraded",
            "database_ok": True,
            "storage_ok": False,
            "storage_detail": "probe timeout",
        },
    )
    response = client.get("/api/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "degraded"

    monkeypatch.setattr(main_module, "diagnostic_snapshot", lambda: {"status": "ready"})
    response = client.get("/api/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_v200_production_template_exposes_storage_timeout_controls() -> None:
    template = sanitized_environment_template()
    assert "S3_CONNECT_TIMEOUT_SECONDS=5" in template
    assert "S3_READ_TIMEOUT_SECONDS=30" in template
    assert "S3_MAX_ATTEMPTS=3" in template
    assert "EXTERNAL_PROBE_TIMEOUT_SECONDS=3" in template
