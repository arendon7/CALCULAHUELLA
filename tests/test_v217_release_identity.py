from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.product_experience import navigation_for
from app.release_candidate import release_candidate_summary

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "app" / "templates" / "consolidation.html"
CANONICAL_DECLARATION = ROOT / "CANONICAL_RELEASE.md"
CANONICAL_MANIFEST = ROOT / "RELEASE_CANONICA.json"


@pytest.mark.smoke
def test_v217_release_identity_separates_semver_web_line_and_historical_snapshot() -> None:
    summary = release_candidate_summary(
        ROOT,
        critical_open=0,
        approved_gates=1,
        gate_count=1,
        validated_journeys=1,
        journey_count=1,
    )
    identity = summary["identity"]
    snapshot = identity["canonical_snapshot"]

    assert identity["application_version"] == "1.0.0"
    assert identity["web_certification_line"] == "V2.1.5 post-RC web"
    assert "CI completo" in identity["web_certification_source"]
    assert snapshot["status"] == "available"
    assert snapshot["release_id"] == "v1.0.0-canonica.20260805"
    assert snapshot["canonical_date"] == "2026-08-05"
    assert snapshot["application_version"] == "1.0.0"
    assert snapshot["migration_head"] == "20260805_0036"
    assert identity["snapshot_matches_application_version"] is True


@pytest.mark.smoke
def test_v217_historical_manifest_is_preserved_as_snapshot_evidence() -> None:
    manifest = json.loads(CANONICAL_MANIFEST.read_text(encoding="utf-8"))
    declaration = CANONICAL_DECLARATION.read_text(encoding="utf-8")

    assert manifest["release_id"] == "v1.0.0-canonica.20260805"
    assert manifest["application_version"] == "1.0.0"
    assert manifest["migration_head"] == "20260805_0036"
    assert "snapshot histórico de canonicalización" in declaration
    assert "no implica por sí sola un cambio de versión semántica" in declaration


@pytest.mark.smoke
def test_v217_consolidation_explains_identity_and_navigation_names_governance() -> None:
    template = TEMPLATE.read_text(encoding="utf-8")
    navigation = navigation_for(
        {
            "role": "Administrador",
            "capabilities": {"view_consolidation", "manage_consolidation"},
        },
        "complete",
    )
    release_entries = [
        item["label"]
        for section in navigation["internal"]
        for item in section["items"]
        if item["href"] == "/consolidacion"
    ]

    assert release_entries == ["Gobierno de release"]
    assert "Gobierno de release e identidad técnica" in template
    assert "Tres referencias con funciones distintas" in template
    assert "Versión de aplicación" in template
    assert "Línea de certificación web" in template
    assert "Snapshot canónico histórico" in template
    assert "La evolución de la web no cambia automáticamente la versión semántica" in template
