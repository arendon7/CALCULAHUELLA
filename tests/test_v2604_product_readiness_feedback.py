from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "iteration4-stabilization.yml"
V2606_FAST_GATE = ROOT / ".github" / "workflows" / "v2606-revenue-operations-gate.yml"

ACTIVE_RELEASE_CONTRACTS = (
    "tests/test_v259_render_release_identity_gate.py",
    "tests/test_v2602_public_diagnosis_trust_consent.py",
    "tests/test_v2603_public_result_interpretation.py",
    "tests/test_v260_public_diagnosis_value_hierarchy.py",
    "tests/test_v260_public_experience_evidence_safe.py",
    "tests/test_v260_public_handoff_taxonomy.py",
    "tests/test_v260_public_result_visual_contract.py",
    "tests/test_v260_solution_plan_alignment.py",
    "tests/test_v2604_product_readiness_feedback.py",
    "tests/test_v2605_commercial_authority.py",
)


def _workflow_sections() -> tuple[str, str]:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    targeted_marker = "- name: Ejecutar contratos de product readiness"
    migration_marker = "- name: Migración desde base vacía"
    full_marker = "- name: Suite integral aislada"
    targeted_start = workflow.index(targeted_marker)
    targeted_end = workflow.index(migration_marker, targeted_start)
    full_start = workflow.index(full_marker, targeted_end)
    assert targeted_start < targeted_end < full_start
    return workflow[targeted_start:targeted_end], workflow[full_start:]


def test_v2604_active_release_contracts_run_in_exact_early_gate() -> None:
    targeted, full = _workflow_sections()

    for contract in ACTIVE_RELEASE_CONTRACTS:
        assert contract in targeted, f"Contrato activo fuera del gate dirigido temprano: {contract}"

    assert "pytest -q" in targeted
    assert "--junitxml=iteration4-targeted.xml" in targeted
    assert "python scripts/run_test_tier.py full --durations 5 --timeout 420" in full


def test_v2604_full_regression_remains_exhaustive_after_fast_feedback() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "Suite integral aislada" in workflow
    assert "python scripts/run_test_tier.py full --durations 5 --timeout 420" in workflow
    assert "--deselect=tests/test_v259" not in workflow
    assert "--deselect=tests/test_v260" not in workflow


def test_v2606_revenue_truth_has_dedicated_early_gate_without_reducing_full_regression() -> None:
    source = V2606_FAST_GATE.read_text(encoding="utf-8")

    assert "V2.60.6 · Revenue operations truth gate" in source
    assert "Revenue truth · fast feedback" in source
    assert "Contratos Revenue Operations" in source
    assert "pytest -q tests/test_v2606_revenue_operations_truth.py" in source
    assert "Fresh migration SQLite" in source
    assert "Upgrade histórico 0040 a head SQLite" in source
    assert "20260824_0041_v2606_revenue_operations_truth.py" in source

    full_workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "python scripts/run_test_tier.py full --durations 5 --timeout 420" in full_workflow
