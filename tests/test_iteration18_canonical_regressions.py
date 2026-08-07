from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.database import Base
from app.main import app
from app.release_candidate import release_candidate_summary

ROOT = Path(__file__).resolve().parents[1]


def _login(client: TestClient, email: str = "consultor@calculatuhuella.local") -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_iteration18_public_contract_supersedes_legacy_v049_v051_copy() -> None:
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        text = response.text
        assert "Toda tu gestión de carbono" in text
        assert "Plataforma colaborativa de gestión de carbono" in text
        assert "Potenciado por GREENATICS" in text
        assert "La medición es el punto de partida" in text
        assert "Realizar diagnóstico" in text
        assert "no actúa automáticamente como organismo verificador o certificador" in text
        assert "Mide lo que corresponde" not in text
        assert "PLANES Y PRECIOS DE REFERENCIA" not in text


def test_iteration18_schema_includes_transversal_workflow_tables() -> None:
    migration = ROOT / "migrations" / "versions" / "20260806_0037_canonical_work_items.py"
    assert migration.is_file()
    assert len(Base.metadata.tables) == 124
    for table in ("work_items", "work_item_events", "work_item_links", "work_item_dependencies"):
        assert table in Base.metadata.tables


def test_iteration18_guide_uses_eight_stage_canonical_cycle_and_boundaries() -> None:
    with TestClient(app) as client:
        _login(client, "cliente@calculatuhuella.local")
        page = client.get("/guia")
        assert page.status_code == 200
        text = page.text
        assert "Ocho preguntas que ordenan el ciclo" in text
        assert "QUÉ HACE Y QUÉ NO HACE" in text
        assert "Dato de actividad" in text
        assert "Emisión evitada" in text
        assert "Compensación" in text
        assert "verificación independiente" in text


def test_iteration18_canonical_release_artifacts_replace_legacy_v051_documents() -> None:
    assert (ROOT / "CANONICAL_RELEASE.md").is_file()
    assert (ROOT / "RELEASE_CANONICA.json").is_file()
    assert (ROOT / "MANIFIESTO_SHA256_CANONICO.txt").is_file()
    assert (ROOT / "app" / "templates" / "guide.html").is_file()
    assert (ROOT / "docs" / "ITERACION_4_ESTABILIZACION.md").is_file()


def test_iteration18_current_repository_keeps_controlled_release_closed_without_test_evidence() -> None:
    summary = release_candidate_summary(
        ROOT,
        critical_open=0,
        approved_gates=9,
        gate_count=9,
        validated_journeys=5,
        journey_count=5,
    )
    assert summary["version"] == "1.0.0"
    assert summary["test_evidence"]["status"] == "missing"
    assert summary["controlled_release_ready"] is False
    assert summary["production_ready"] is False
    assert all(item["ok"] is False for item in summary["external_checks"])


def test_iteration18_structural_validator_is_conservative_without_formal_internal_bundle() -> None:
    from scripts.validate_release_candidate import inspect_candidate

    payload = inspect_candidate()
    checks = {item["code"]: item for item in payload["checks"]}
    assert payload["status"] == "failed"
    assert checks["version"]["ok"] is True
    assert checks["routes"]["ok"] is True
    assert checks["models"]["ok"] is True
    assert checks["templates"]["ok"] is True
    assert checks["migration_head"]["ok"] is True
    assert checks["legal_surface"]["ok"] is True
    assert checks["controlled_release_defaults"]["ok"] is True
    assert checks["public_production_conservative"]["ok"] is True
    assert checks["internal_acceptance"]["ok"] is False


def test_iteration18_formal_legacy_acceptance_bundle_is_not_silently_inferred() -> None:
    formal_bundle = (
        "ACTA_CIERRE_V1_0_0.md",
        "APROBACION_METODOLOGICA_V1_CARLOS_URIBE.md",
        "APROBACION_JURIDICA_V1_AGUSTIN_RENDON.md",
        "INFORME_PILOTO_INTERNO_GREENATICS_V1.md",
        "INFORME_PILOTO_INTERNO_SEGUNDO_SECTOR_V1.md",
        "REVISION_SEGURIDAD_INTERNA_OWASP_ASVS_V1.md",
        "GUIA_LANZAMIENTO_CONTROLADO_V1.md",
    )
    assert any(not (ROOT / name).is_file() for name in formal_bundle)
    assert not (ROOT / "release" / "FINAL_TEST_EVIDENCE.json").is_file()
