from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace

from app.capture_guidance import capture_summary
from scripts.product_readiness_contracts import TARGETED_CONTRACTS


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "iteration4-stabilization.yml"
CLIMATE_GATE = ROOT / "scripts" / "browser_climate_journey_gate.py"


def _workflow() -> str:
    assert WORKFLOW.is_file()
    return WORKFLOW.read_text(encoding="utf-8")


def test_v200_product_readiness_gate_targets_current_v19_baseline() -> None:
    source = _workflow()
    assert "refactor/v1-9-0-core-surfaces" in source
    assert "integration/workflow-v1.5.0" not in source
    assert "integration/uiux-v1.4.0" not in source
    assert "pull_request:" in source
    assert "workflow_dispatch:" in source


def test_v200_product_readiness_gate_includes_operational_security_contracts() -> None:
    source = _workflow()
    required_tests = (
        "tests/test_iteration15_canonical_workflow.py",
        "tests/test_iteration16_area_assignment.py",
        "tests/test_iteration16_work_items.py",
        "tests/test_iteration17_integrated_workflow.py",
        "tests/test_iteration18_stabilization.py",
        "tests/test_iteration19_role_journeys.py",
        "tests/test_v024_security_hardening.py",
        "tests/test_v030_mac_lifecycle.py",
        "tests/test_v034_operational_hardening.py",
        "tests/test_v057_production_readiness.py",
        "tests/test_v100_rc1_release_candidate.py",
        "tests/test_v200_product_readiness_gate.py",
    )
    authority = set(TARGETED_CONTRACTS)
    assert "python scripts/product_readiness_contracts.py" in source
    for test_path in required_tests:
        assert test_path in authority


def test_v200_product_readiness_gate_keeps_real_browser_and_role_journeys() -> None:
    source = _workflow()
    assert "browser: [chromium, firefox, webkit]" in source
    assert "python scripts/browser_workflow_gate.py" in source
    assert "python scripts/browser_role_gate.py" in source
    assert "python scripts/browser_handoff_gate.py" in source


def test_v200_product_readiness_gate_covers_full_climate_journey() -> None:
    source = _workflow()
    assert "Huella completa · Chromium" in source
    assert "CLIMATE_GATE_BASE_URL: http://127.0.0.1:8768" in source
    assert "CLIMATE_GATE_ARTIFACT_DIR: climate-gate-artifacts" in source
    assert "python scripts/browser_climate_journey_gate.py" in source
    assert "climate-journey-evidence" in source


def test_v200_climate_gate_distinguishes_temporal_coverage_from_support_backlog() -> None:
    source = CLIMATE_GATE.read_text(encoding="utf-8")
    assert 'uncovered = [' in source
    assert 'float(summary["coverage"]) != 100 or uncovered' in source
    terminal_block = source.split("if not pending:", 1)[1].split("item = pending[0]", 1)[0]
    assert 'pending_sources' not in terminal_block
    assert 'support_coverage' not in terminal_block


def test_v200_guided_capture_excludes_supplier_managed_aggregate() -> None:
    record = SimpleNamespace(
        id=1,
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        evidence_id=None,
        status="Cargado",
    )
    operational = SimpleNamespace(
        included=True,
        category="Combustión fija",
        data_frequency="Anual",
        preferred_unit="L",
        name="Diésel",
        scope=1,
        materiality="Alta",
        activity_records=[record],
    )
    supplier_aggregate = SimpleNamespace(
        included=True,
        category="Datos específicos de proveedores",
        data_frequency="Anual",
        preferred_unit="tCO₂e",
        name="Cadena de valor consolidada desde proveedores",
        scope=3,
        materiality="Alta",
        activity_records=[],
        progress=50,
    )
    inventory = SimpleNamespace(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        sources=[operational, supplier_aggregate],
    )

    summary = capture_summary(inventory)

    assert summary["sources"] == 1
    assert summary["coverage"] == 100
    assert [item["source"].name for item in summary["cards"]] == ["Diésel"]


def test_v200_climate_gate_reports_source_progress_when_quality_gate_blocks() -> None:
    source = CLIMATE_GATE.read_text(encoding="utf-8")
    assert 'source_state = [' in source
    assert '"progress": item.progress' in source
    assert 'Estado de fuentes: {source_state}' in source


def test_v200_product_readiness_gate_keeps_full_release_barriers() -> None:
    source = _workflow()
    assert "python tools/verify_canonical.py --skip-manifest" in source
    assert "python scripts/audit_architecture.py --enforce" in source
    assert "python scripts/run_test_tier.py smoke" in source
    assert "python scripts/run_test_tier.py full" in source
    assert 'python -m alembic upgrade head' in source
    assert 'python -m alembic upgrade 20260805_0036' in source
    assert "iteration4-targeted.xml" in source
    assert "iteration4-full.log" in source
