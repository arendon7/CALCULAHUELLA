from __future__ import annotations

from pathlib import Path

import pytest

from scripts.product_readiness_contracts import (
    ContractAuthorityError,
    EXCLUDED_VERSIONED_CONTRACTS,
    TARGETED_CONTRACTS,
    TRANSVERSAL_CONTRACTS,
    VERSIONED_GLOBS,
    execution_plan,
    validate_authority,
)


ROOT = Path(__file__).resolve().parents[1]
V26013_WORKFLOW = ROOT / ".github" / "workflows" / "v26013-product-readiness-contract-authority-gate.yml"


def _write(root: Path, relative_path: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("def test_contract():\n    assert True\n", encoding="utf-8")


def test_product_readiness_authority_covers_current_repository() -> None:
    discovered = validate_authority()

    assert discovered
    assert all(
        Path(path).name.startswith(("test_v260", "test_v261"))
        for path in discovered
    )
    assert "tests/test_v261_visible_demo_data_labels.py" in discovered
    assert "tests/test_v261_visible_demo_data_labels.py" in TARGETED_CONTRACTS
    assert "test_v260*.py" in VERSIONED_GLOBS
    assert "test_v261*.py" in VERSIONED_GLOBS
    assert len(execution_plan()) == len(TARGETED_CONTRACTS) + len(TRANSVERSAL_CONTRACTS)
    assert not EXCLUDED_VERSIONED_CONTRACTS


@pytest.mark.parametrize(
    ("known", "future"),
    (
        ("tests/test_v2606_known.py", "tests/test_v26099_future_contract.py"),
        ("tests/test_v261_known.py", "tests/test_v26199_future_contract.py"),
    ),
)
def test_product_readiness_authority_rejects_unclassified_future_contract(
    tmp_path: Path,
    known: str,
    future: str,
) -> None:
    _write(tmp_path, known)
    _write(tmp_path, future)

    with pytest.raises(ContractAuthorityError, match="contratos sin clasificar"):
        validate_authority(
            tmp_path,
            targeted=(known,),
            transversal=(),
            excluded={},
        )


def test_product_readiness_authority_rejects_stale_or_missing_classification(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "tests/test_v261_known.py")

    with pytest.raises(ContractAuthorityError) as exc_info:
        validate_authority(
            tmp_path,
            targeted=(
                "tests/test_v261_known.py",
                "tests/test_v261_missing.py",
            ),
            transversal=(),
            excluded={},
        )

    message = str(exc_info.value)
    assert "Contrato clasificado inexistente: tests/test_v261_missing.py" in message
    assert "Autoridad versionada obsoleta" in message


def test_product_readiness_authority_rejects_duplicates_and_overlap(tmp_path: Path) -> None:
    _write(tmp_path, "tests/test_v261_known.py")

    with pytest.raises(ContractAuthorityError) as exc_info:
        validate_authority(
            tmp_path,
            targeted=("tests/test_v261_known.py", "tests/test_v261_known.py"),
            transversal=("tests/test_v261_known.py",),
            excluded={},
        )

    message = str(exc_info.value)
    assert "TARGETED_CONTRACTS contiene duplicados" in message
    assert "Clasificación solapada targeted/transversal" in message


def test_product_readiness_authority_requires_reason_for_exclusion(tmp_path: Path) -> None:
    _write(tmp_path, "tests/test_v261_known.py")
    _write(tmp_path, "tests/test_v261_auxiliary.py")

    with pytest.raises(ContractAuthorityError, match="Exclusión sin justificación"):
        validate_authority(
            tmp_path,
            targeted=("tests/test_v261_known.py",),
            transversal=(),
            excluded={"tests/test_v261_auxiliary.py": "   "},
        )


def test_product_readiness_authority_accepts_explicit_reasoned_exclusion(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "tests/test_v261_known.py")
    _write(tmp_path, "tests/test_v261_auxiliary.py")

    discovered = validate_authority(
        tmp_path,
        targeted=("tests/test_v261_known.py",),
        transversal=(),
        excluded={
            "tests/test_v261_auxiliary.py": "Auxiliary harness contract covered by its canonical replacement."
        },
    )

    assert discovered == (
        "tests/test_v261_auxiliary.py",
        "tests/test_v261_known.py",
    )


def test_product_readiness_execution_plan_keeps_transversal_contracts_isolated() -> None:
    plan = execution_plan(
        targeted=("tests/test_v2606_known.py", "tests/test_v261_known.py"),
        transversal=("tests/test_migration_legacy_compat.py",),
    )

    assert plan == (
        "tests/test_v2606_known.py",
        "tests/test_v261_known.py",
        "tests/test_migration_legacy_compat.py",
    )


def test_v26013_gate_triggers_for_v261_contract_family() -> None:
    source = V26013_WORKFLOW.read_text(encoding="utf-8")

    assert '- "tests/test_v260*.py"' in source
    assert '- "tests/test_v261*.py"' in source
    assert "Validar inventario y drift versionado" in source


def test_v26013_evidence_distinguishes_certified_head_from_synthetic_checkout() -> None:
    source = V26013_WORKFLOW.read_text(encoding="utf-8")

    assert "CERTIFIED_HEAD_SHA: ${{ github.event.pull_request.head.sha || github.sha }}" in source
    assert 'echo "certified_head_sha=${CERTIFIED_HEAD_SHA}"' in source
    assert 'echo "checked_out_sha=$(git rev-parse HEAD)"' in source
    assert 'echo "github_sha=${GITHUB_SHA}"' in source
    assert "v26013-certified-identity.txt" in source
