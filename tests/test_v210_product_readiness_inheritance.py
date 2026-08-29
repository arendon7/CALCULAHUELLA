from pathlib import Path

from scripts.product_readiness_contracts import TARGETED_CONTRACTS


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "iteration4-stabilization.yml"


def workflow_source() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_v210_full_gate_accepts_v19_and_certified_v20_bases() -> None:
    source = workflow_source()
    assert "- refactor/v1-9-0-core-surfaces" in source
    assert "- stabilization/v2-0-0-product-readiness" in source
    assert "types: [opened, synchronize, reopened, ready_for_review]" in source


def test_v210_brand_contracts_are_inside_targeted_release_gate() -> None:
    source = workflow_source()
    authority = set(TARGETED_CONTRACTS)

    assert "python scripts/product_readiness_contracts.py" in source
    assert "tests/test_v210_brand_provenance.py" in authority
    assert "tests/test_v210_brand_package.py" in authority


def test_v210_inheritance_keeps_all_v20_release_barriers() -> None:
    source = workflow_source()
    required = (
        "python tools/verify_canonical.py --skip-manifest",
        "python scripts/audit_architecture.py --enforce",
        "python scripts/run_test_tier.py smoke",
        "python scripts/run_test_tier.py full",
        "Continuidad · restore PostgreSQL real",
        "browser: [chromium, firefox, webkit]",
        "python scripts/browser_workflow_gate.py",
        "python scripts/browser_role_gate.py",
        "python scripts/browser_handoff_gate.py",
        "python scripts/browser_climate_journey_gate.py",
    )
    for contract in required:
        assert contract in source
