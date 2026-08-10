from __future__ import annotations

import importlib.util
from pathlib import Path

from app.release_candidate import _evidence_file_exists


ROOT = Path(__file__).resolve().parents[1]


def _load_architecture_audit_module():
    path = ROOT / "scripts" / "audit_architecture.py"
    spec = importlib.util.spec_from_file_location("audit_architecture_v160", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_architecture_snapshot_stays_within_v155_debt_ceiling():
    audit = _load_architecture_audit_module()
    data = audit.snapshot()
    assert data["main_lines"] > 0
    assert data["database_lines"] > 0
    assert data["total_routes"] > 0
    assert data["orm_tables"] > 0
    assert audit.regressions(data) == []


def test_architecture_audit_exposes_remaining_hotspots_and_recognizes_extracted_lifecycle():
    audit = _load_architecture_audit_module()
    data = audit.snapshot()
    hotspots = data["main_function_hotspots"]
    assert hotspots
    assert all(int(item["lines"]) > 0 for item in hotspots)
    # `clone_inventory_version` was the former ~190-line hotspot. Once its
    # lifecycle service is extracted, governance must reward the reduction
    # instead of requiring the debt to remain in main.py.
    assert all(item["name"] != "clone_inventory_version" for item in hotspots)
    assert max(int(item["lines"]) for item in hotspots) < 190
    assert (ROOT / "app" / "inventory_lifecycle.py").is_file()


def test_release_evidence_accepts_current_document_tree(tmp_path: Path):
    canonical = tmp_path / "docs" / "gobierno" / "ACTA_CIERRE_V1_0_0.md"
    canonical.parent.mkdir(parents=True)
    canonical.write_text("aprobado", encoding="utf-8")
    assert _evidence_file_exists(
        tmp_path,
        "docs/gobierno/ACTA_CIERRE_V1_0_0.md",
        "ACTA_CIERRE_V1_0_0.md",
    )


def test_release_evidence_keeps_legacy_compatibility(tmp_path: Path):
    legacy = tmp_path / "ACTA_CIERRE_V1_0_0.md"
    legacy.write_text("aprobado", encoding="utf-8")
    assert _evidence_file_exists(
        tmp_path,
        "docs/gobierno/ACTA_CIERRE_V1_0_0.md",
        "ACTA_CIERRE_V1_0_0.md",
    )
