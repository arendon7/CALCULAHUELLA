from __future__ import annotations

from pathlib import Path

import pytest

from scripts.product_readiness_contracts import (
    ContractAuthorityError,
    EXCLUDED_VERSIONED_CONTRACTS,
    TARGETED_CONTRACTS,
    TRANSVERSAL_CONTRACTS,
    execution_plan,
    validate_authority,
)


def _write(root: Path, relative_path: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("def test_contract():\n    assert True\n", encoding="utf-8")


def test_product_readiness_authority_covers_current_repository() -> None:
    discovered = validate_authority()

    assert discovered
    assert all(Path(path).name.startswith("test_v260") for path in discovered)
    assert len(execution_plan()) == len(TARGETED_CONTRACTS) + len(TRANSVERSAL_CONTRACTS)
    assert not EXCLUDED_VERSIONED_CONTRACTS


def test_product_readiness_authority_rejects_unclassified_future_v260_contract(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "tests/test_v2606_known.py")
    _write(tmp_path, "tests/test_v26099_future_contract.py")

    with pytest.raises(ContractAuthorityError, match="contratos sin clasificar"):
        validate_authority(
            tmp_path,
            targeted=("tests/test_v2606_known.py",),
            transversal=(),
            excluded={},
        )


def test_product_readiness_authority_rejects_stale_or_missing_classification(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "tests/test_v2606_known.py")

    with pytest.raises(ContractAuthorityError) as exc_info:
        validate_authority(
            tmp_path,
            targeted=(
                "tests/test_v2606_known.py",
                "tests/test_v2607_missing.py",
            ),
            transversal=(),
            excluded={},
        )

    message = str(exc_info.value)
    assert "Contrato clasificado inexistente: tests/test_v2607_missing.py" in message
    assert "Autoridad V2.60 obsoleta" in message


def test_product_readiness_authority_rejects_duplicates_and_overlap(tmp_path: Path) -> None:
    _write(tmp_path, "tests/test_v2606_known.py")

    with pytest.raises(ContractAuthorityError) as exc_info:
        validate_authority(
            tmp_path,
            targeted=("tests/test_v2606_known.py", "tests/test_v2606_known.py"),
            transversal=("tests/test_v2606_known.py",),
            excluded={},
        )

    message = str(exc_info.value)
    assert "TARGETED_CONTRACTS contiene duplicados" in message
    assert "Clasificación solapada targeted/transversal" in message


def test_product_readiness_authority_requires_reason_for_exclusion(tmp_path: Path) -> None:
    _write(tmp_path, "tests/test_v2606_known.py")
    _write(tmp_path, "tests/test_v2607_auxiliary.py")

    with pytest.raises(ContractAuthorityError, match="Exclusión sin justificación"):
        validate_authority(
            tmp_path,
            targeted=("tests/test_v2606_known.py",),
            transversal=(),
            excluded={"tests/test_v2607_auxiliary.py": "   "},
        )


def test_product_readiness_authority_accepts_explicit_reasoned_exclusion(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "tests/test_v2606_known.py")
    _write(tmp_path, "tests/test_v2607_auxiliary.py")

    discovered = validate_authority(
        tmp_path,
        targeted=("tests/test_v2606_known.py",),
        transversal=(),
        excluded={
            "tests/test_v2607_auxiliary.py": "Auxiliary harness contract covered by its canonical replacement."
        },
    )

    assert discovered == (
        "tests/test_v2606_known.py",
        "tests/test_v2607_auxiliary.py",
    )


def test_product_readiness_execution_plan_keeps_transversal_contracts_isolated() -> None:
    plan = execution_plan(
        targeted=("tests/test_v2606_known.py", "tests/test_v2607_known.py"),
        transversal=("tests/test_migration_legacy_compat.py",),
    )

    assert plan == (
        "tests/test_v2606_known.py",
        "tests/test_v2607_known.py",
        "tests/test_migration_legacy_compat.py",
    )
