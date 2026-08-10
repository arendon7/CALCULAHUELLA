from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "iteration4-stabilization.yml"


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
    for test_path in required_tests:
        assert test_path in source


def test_v200_product_readiness_gate_keeps_real_browser_and_role_journeys() -> None:
    source = _workflow()
    assert "browser: [chromium, firefox, webkit]" in source
    assert "python scripts/browser_workflow_gate.py" in source
    assert "python scripts/browser_role_gate.py" in source
    assert "python scripts/browser_handoff_gate.py" in source


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
