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


def test_v0461_recovers_lineage_and_optional_deployment_with_current_github_contract():
    assert (ROOT / "CANONICAL_RELEASE.md").exists()
    assert (ROOT / "RELEASE_CANONICA.json").exists()
    render = ROOT / "deployment" / "render.example.yaml"
    assert render.exists()
    assert "autoDeploy: false" in render.read_text(encoding="utf-8")
    # GitHub is now part of the canonical delivery contract rather than an
    # optional dependency that must be absent from the package.
    assert (ROOT / ".github" / "workflows" / "ci.yml").exists()


def test_v0461_local_validation_and_certification_entrypoints_are_current():
    validator = ROOT / "18_VALIDAR_VERSION_FINAL_V1.command"
    certification = ROOT / "19_CERTIFICAR_INSTALACION.command"
    assert validator.is_file()
    assert certification.is_file()

    validation_text = validator.read_text(encoding="utf-8")
    certification_text = certification.read_text(encoding="utf-8")
    assert "V1.0.0" in validation_text
    assert "validate_release_candidate.py" in validation_text
    assert "pytest -q" in validation_text
    assert "platform_preflight.py" in certification_text
    assert "run_test_tier.py smoke" in certification_text
    assert "run_acceptance_certification.py" in certification_text

    modules = (ROOT / "app" / "templates" / "modules.html").read_text(encoding="utf-8")
    assert "V1.0.0 · estabilización" in modules
    assert "105 modelos ORM" not in modules
    assert "112 modelos ORM" in modules
