from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]

# Single source of truth for the focused Product Readiness certification layer.
# Keep historical contracts already enforced by iteration4-stabilization.yml and
# classify every versioned adoption contract explicitly. The drift guard below
# makes new V2.60/V2.61/V2.62 contracts fail closed until deliberately classified here.
TARGETED_CONTRACTS: tuple[str, ...] = (
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
    "tests/test_v200_postgres_continuity_gate.py",
    "tests/test_v200_postgres_schema_compatibility.py",
    "tests/test_v200_postgres_methodology_schema.py",
    "tests/test_v210_brand_provenance.py",
    "tests/test_v210_brand_package.py",
    "tests/test_v259_render_release_identity_gate.py",
    "tests/test_v260_public_diagnosis_value_hierarchy.py",
    "tests/test_v260_public_experience_evidence_safe.py",
    "tests/test_v260_public_handoff_taxonomy.py",
    "tests/test_v260_public_result_visual_contract.py",
    "tests/test_v260_solution_plan_alignment.py",
    "tests/test_v2602_public_diagnosis_trust_consent.py",
    "tests/test_v2603_public_result_interpretation.py",
    "tests/test_v2604_product_readiness_feedback.py",
    "tests/test_v2605_commercial_authority.py",
    "tests/test_v2606_revenue_operations_truth.py",
    "tests/test_v2606_activation_invoice_integrity.py",
    "tests/test_v2607_monetary_precision.py",
    "tests/test_v2608_monetary_boundaries.py",
    "tests/test_v2608_bind_policy.py",
    "tests/test_v2609_numeric_range_integrity.py",
    "tests/test_v2609_orm_flush_guard.py",
    "tests/test_v26010_monetary_authority_consolidation.py",
    "tests/test_v26010_1_decimal_integration_closure.py",
    "tests/test_v26011_revenue_actionability.py",
    "tests/test_v26011_revenue_actionability_web.py",
    "tests/test_v26012_commercial_lifecycle_policy.py",
    "tests/test_v26012_commercial_lifecycle_integrity.py",
    "tests/test_v26012_hash_boundaries.py",
    "tests/test_v261_visible_demo_data_labels.py",
    "tests/test_v262_mobile_operational_priority.py",
)

# Cross-version compatibility contracts belong to Product Readiness but are not
# part of the current versioned naming families, so they are tracked separately.
TRANSVERSAL_CONTRACTS: tuple[str, ...] = (
    "tests/test_v210_product_readiness_inheritance.py",
    "tests/test_migration_legacy_compat.py",
)

# A versioned module may be excluded only by naming it here with a non-empty reason.
# Empty by design: current V2.60/V2.61/V2.62 contracts are adoption-relevant.
EXCLUDED_VERSIONED_CONTRACTS: dict[str, str] = {}

VERSIONED_GLOBS: tuple[str, ...] = (
    "test_v260*.py",
    "test_v261*.py",
    "test_v262*.py",
)
VERSIONED_PREFIXES: tuple[str, ...] = (
    "test_v260",
    "test_v261",
    "test_v262",
)


class ContractAuthorityError(RuntimeError):
    """Raised when Product Readiness contract authority is incomplete or stale."""


def discover_versioned_contracts(root: Path = ROOT) -> tuple[str, ...]:
    tests_root = root / "tests"
    discovered = {
        path.relative_to(root).as_posix()
        for pattern in VERSIONED_GLOBS
        for path in tests_root.glob(pattern)
    }
    return tuple(sorted(discovered))


def _is_versioned_contract(relative_path: str) -> bool:
    name = Path(relative_path).name
    return any(name.startswith(prefix) for prefix in VERSIONED_PREFIXES)


def _duplicates(values: Sequence[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def validate_authority(
    root: Path = ROOT,
    *,
    targeted: Sequence[str] = TARGETED_CONTRACTS,
    transversal: Sequence[str] = TRANSVERSAL_CONTRACTS,
    excluded: Mapping[str, str] = EXCLUDED_VERSIONED_CONTRACTS,
) -> tuple[str, ...]:
    errors: list[str] = []
    targeted_tuple = tuple(targeted)
    transversal_tuple = tuple(transversal)
    excluded_paths = tuple(excluded)

    for label, values in (
        ("TARGETED_CONTRACTS", targeted_tuple),
        ("TRANSVERSAL_CONTRACTS", transversal_tuple),
        ("EXCLUDED_VERSIONED_CONTRACTS", excluded_paths),
    ):
        duplicates = sorted(_duplicates(values))
        if duplicates:
            errors.append(f"{label} contiene duplicados: {', '.join(duplicates)}")

    overlaps = {
        "targeted/transversal": set(targeted_tuple) & set(transversal_tuple),
        "targeted/excluded": set(targeted_tuple) & set(excluded_paths),
        "transversal/excluded": set(transversal_tuple) & set(excluded_paths),
    }
    for label, values in overlaps.items():
        if values:
            errors.append(f"Clasificación solapada {label}: {', '.join(sorted(values))}")

    for relative_path in (*targeted_tuple, *transversal_tuple, *excluded_paths):
        path = root / relative_path
        if not path.is_file():
            errors.append(f"Contrato clasificado inexistente: {relative_path}")

    for relative_path, reason in excluded.items():
        if not str(reason).strip():
            errors.append(f"Exclusión sin justificación: {relative_path}")

    discovered = set(discover_versioned_contracts(root))
    classified_versioned = {
        path for path in targeted_tuple if _is_versioned_contract(path)
    } | set(excluded_paths)

    unclassified = sorted(discovered - classified_versioned)
    stale = sorted(classified_versioned - discovered)
    if unclassified:
        errors.append(
            "Drift versionado: contratos sin clasificar: " + ", ".join(unclassified)
        )
    if stale:
        errors.append(
            "Autoridad versionada obsoleta: rutas clasificadas que ya no existen en las familias controladas: "
            + ", ".join(stale)
        )

    if errors:
        raise ContractAuthorityError("\n".join(f"- {error}" for error in errors))

    return tuple(sorted(discovered))


def execution_plan(
    targeted: Sequence[str] = TARGETED_CONTRACTS,
    transversal: Sequence[str] = TRANSVERSAL_CONTRACTS,
) -> tuple[str, ...]:
    return (*tuple(targeted), *tuple(transversal))


def _run_isolated_pytest(
    relative_path: str,
    *,
    timeout_seconds: int,
    durations: int,
    junit_path: Path | None,
) -> int:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "pytest_isolated.py"),
        "-q",
        relative_path,
    ]
    if durations > 0:
        command.append(f"--durations={durations}")
    if junit_path is not None:
        command.append(f"--junitxml={junit_path}")

    environment = os.environ.copy()
    environment.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    with tempfile.TemporaryDirectory(prefix="cth_product_readiness_") as temporary_root:
        environment["TMPDIR"] = temporary_root
        environment["TEMP"] = temporary_root
        environment["TMP"] = temporary_root
        print(" ".join(command), flush=True)
        try:
            return subprocess.run(
                command,
                cwd=ROOT,
                env=environment,
                check=False,
                timeout=max(30, timeout_seconds),
            ).returncode
        except subprocess.TimeoutExpired:
            print(
                f"TIMEOUT · {relative_path} superó {max(30, timeout_seconds)} segundos.",
                file=sys.stderr,
                flush=True,
            )
            return 124


def _append_synthetic_failure(
    aggregate: ET.Element,
    *,
    relative_path: str,
    return_code: int,
) -> None:
    suite = ET.SubElement(
        aggregate,
        "testsuite",
        {
            "name": f"product-readiness::{relative_path}",
            "tests": "1",
            "failures": "1",
            "errors": "0",
            "skipped": "0",
            "time": "0",
        },
    )
    case = ET.SubElement(
        suite,
        "testcase",
        {"classname": "product_readiness_contract_authority", "name": relative_path},
    )
    failure = ET.SubElement(case, "failure", {"message": f"isolated pytest exit {return_code}"})
    failure.text = f"No JUnit payload was produced; isolated pytest exited with code {return_code}."


def _merge_junit(
    child_reports: Sequence[tuple[str, Path, int]],
    destination: Path,
) -> None:
    aggregate = ET.Element("testsuites")
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    total_time = 0.0

    for relative_path, report_path, return_code in child_reports:
        if report_path.is_file():
            root = ET.parse(report_path).getroot()
            suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
            for suite in suites:
                aggregate.append(suite)
                for key in totals:
                    totals[key] += int(float(suite.attrib.get(key, "0") or 0))
                total_time += float(suite.attrib.get("time", "0") or 0)
        else:
            _append_synthetic_failure(
                aggregate,
                relative_path=relative_path,
                return_code=return_code,
            )
            totals["tests"] += 1
            totals["failures"] += 1

    aggregate.attrib.update({key: str(value) for key, value in totals.items()})
    aggregate.set("time", f"{total_time:.6f}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(aggregate).write(destination, encoding="utf-8", xml_declaration=True)


def run_contracts(
    *,
    timeout_seconds: int,
    durations: int,
    junit_destination: Path | None,
) -> int:
    validate_authority(ROOT)
    plan = execution_plan()
    failures: list[tuple[str, int]] = []

    with tempfile.TemporaryDirectory(prefix="cth_product_readiness_junit_") as report_root_text:
        report_root = Path(report_root_text)
        reports: list[tuple[str, Path, int]] = []
        for index, relative_path in enumerate(plan, start=1):
            print(
                f"\nContrato Product Readiness {index}/{len(plan)} · {relative_path}",
                flush=True,
            )
            report_path = report_root / f"{index:03d}.xml"
            return_code = _run_isolated_pytest(
                relative_path,
                timeout_seconds=timeout_seconds,
                durations=durations,
                junit_path=report_path if junit_destination is not None else None,
            )
            reports.append((relative_path, report_path, return_code))
            if return_code:
                failures.append((relative_path, return_code))
                print(
                    f"FALLO REGISTRADO · {relative_path} · código {return_code}. Se continúa para completar la autoridad.",
                    flush=True,
                )

        if junit_destination is not None:
            _merge_junit(reports, junit_destination)

    if failures:
        print("\nResumen de fallos Product Readiness:", file=sys.stderr, flush=True)
        for relative_path, return_code in failures:
            print(f"- {relative_path}: código {return_code}", file=sys.stderr, flush=True)
        return 1

    print(
        f"\nProduct Readiness Contract Authority PASS · {len(plan)} módulos aislados.",
        flush=True,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Valida y ejecuta la autoridad focal de contratos Product Readiness."
    )
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--timeout", type=int, default=420)
    parser.add_argument("--durations", type=int, default=0)
    parser.add_argument("--junitxml", type=Path)
    args = parser.parse_args()

    try:
        discovered = validate_authority(ROOT)
    except ContractAuthorityError as exc:
        print("Product Readiness Contract Authority FAIL", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 2

    print(
        "Product Readiness Contract Authority VALID · "
        f"{len(TARGETED_CONTRACTS)} targeted · "
        f"{len(TRANSVERSAL_CONTRACTS)} transversal · "
        f"{len(EXCLUDED_VERSIONED_CONTRACTS)} excluded · "
        f"{len(discovered)} versioned discovered",
        flush=True,
    )
    if args.validate_only:
        return 0

    return run_contracts(
        timeout_seconds=max(30, args.timeout),
        durations=max(0, args.durations),
        junit_destination=args.junitxml,
    )


if __name__ == "__main__":
    raise SystemExit(main())
