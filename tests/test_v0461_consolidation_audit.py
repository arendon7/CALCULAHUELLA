from pathlib import Path

from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app


ROOT = Path(__file__).resolve().parents[1]


def test_v0461_release_is_aligned_and_delivery_remains_available():
    init_db()
    with TestClient(app) as client:
        assert client.get("/api/health").json()["version"] == "1.0.0"
        response = client.post(
            "/login",
            data={"email": "consultor@calculatuhuella.local", "password": "Demo2026!"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert client.get("/entrega-profesional").status_code == 200


def test_v0461_recovers_lineage_and_optional_deployment_without_github_dependency():
    assert (ROOT / "docs" / "BASE_CANONICA_V0455.md").exists()
    assert (ROOT / "docs" / "AUDITORIA_VERSIONES_ANTERIORES_V0461.md").exists()
    assert (ROOT / "deployment" / "render.example.yaml").exists()
    assert "autoDeploy: false" in (ROOT / "deployment" / "render.example.yaml").read_text(encoding="utf-8")
    assert not (ROOT / ".github").exists()


def test_v0461_local_audit_and_current_labels_are_present():
    mac_command = ROOT / "16_AUDITAR_VERSION_COMPLETA.command"
    if mac_command.is_file():
        audit = (ROOT / "scripts" / "audit_release_local.sh").read_text(encoding="utf-8")
        assert "suite integral reproducible" in audit.lower()
        assert '"$PYTHON" -m pytest -q' in audit
        assert "validate_release_candidate.py" in audit
        assert "--record-passed" in audit
        assert "PYTHONPATH" not in audit
        certification = (ROOT / "14_CERTIFICAR_VERSION.command").read_text(encoding="utf-8")
    else:
        assert (ROOT / "6_AUDITAR_VERSION_COMPLETA.bat").is_file()
        audit = (ROOT / "audit_release_windows.ps1").read_text(encoding="utf-8")
        assert "suite integral reproducible" in audit.lower()
        assert "-m pytest -q" in audit
        assert "validate_release_candidate.py" in audit
        assert "--record-passed" in audit
        assert "PYTHONPATH" not in audit
        certification = (ROOT / "5_VALIDAR_VERSION_FINAL_V1.bat").read_text(encoding="utf-8")
    modules = (ROOT / "app" / "templates" / "modules.html").read_text(encoding="utf-8")
    assert "V1.0.0 · estabilización" in modules
    assert "105 modelos ORM" not in modules
    assert "V1.0.0" in certification
