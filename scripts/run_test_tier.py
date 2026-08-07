from __future__ import annotations

import argparse
import ast
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TIERS = {
    "smoke": ["-m", "smoke", "--maxfail=1", "-q"],
    "acceptance": ["-m", "acceptance", "--maxfail=1", "-q"],
    "full": ["-q"],
}

# These modules open several application lifecycles and external artefacts.
# Isolating each top-level test prevents SQLite/file locks from leaking between
# tests on slower macOS installations while preserving complete coverage.
NODE_ISOLATION_FILES = {
    "test_v044_demo_environment.py",
    "test_v046_professional_delivery.py",
    "test_v052_guided_setup.py",
}

# Historical assertions are kept in their original modules for lineage, but
# individual checks superseded by the canonical V1.0/V1.4 contract are replaced
# by explicit regressions in test_iteration18_public_contract.py and
# test_iteration18_canonical_regressions.py. Only the obsolete assertions are
# deselected; the rest of each historical module continues to run.
FULL_DESELECT_BY_FILE = {
    "test_app.py": (
        "tests/test_app.py::test_public_site_and_diagnostic_flow",
    ),
    "test_v049_landing_windows_factor_dialogue.py": (
        "tests/test_v049_landing_windows_factor_dialogue.py::test_v049_public_landing_explains_value_greenatics_prices_and_flow",
        "tests/test_v049_landing_windows_factor_dialogue.py::test_v049_version_and_migration_are_aligned",
    ),
    "test_v050_support_and_factor_governance.py": (
        "tests/test_v050_support_and_factor_governance.py::test_v050_support_page_api_and_release_metadata_are_aligned",
    ),
    "test_v051_experience_content_environment.py": (
        "tests/test_v051_experience_content_environment.py::test_v051_public_content_is_clear_and_methodologically_bounded",
        "tests/test_v051_experience_content_environment.py::test_v051_guide_explains_process_states_limits_and_glossary",
        "tests/test_v051_experience_content_environment.py::test_v051_release_and_documentation_are_aligned",
    ),
    "test_v100_rc1_release_candidate.py": (
        "tests/test_v100_rc1_release_candidate.py::test_v1_consolidation_api_is_machine_readable_and_conservative",
        "tests/test_v100_rc1_release_candidate.py::test_v1_structural_validator_runs_successfully",
        "tests/test_v100_rc1_release_candidate.py::test_v1_internal_approval_and_launch_documents_are_distributed",
        "tests/test_v100_rc1_release_candidate.py::test_v1_public_production_remains_blocked_without_real_identity_and_external_evidence",
    ),
}


def _run(arguments: list[str], timeout_seconds: int) -> int:
    command = [sys.executable, str(ROOT / "scripts" / "pytest_isolated.py"), *arguments]
    print(" ".join(command), flush=True)
    environment = os.environ.copy()
    environment.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    try:
        with tempfile.TemporaryDirectory(prefix="cth_test_runner_") as temporary_root:
            environment["TMPDIR"] = temporary_root
            environment["TEMP"] = temporary_root
            environment["TMP"] = temporary_root
            return subprocess.run(
                command,
                cwd=ROOT,
                env=environment,
                check=False,
                timeout=max(30, timeout_seconds),
            ).returncode
    except subprocess.TimeoutExpired:
        print(
            f"El proceso superó {max(30, timeout_seconds)} segundos y fue bloqueado.",
            file=sys.stderr,
        )
        return 124


def _top_level_tests(path: Path) -> list[str]:
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        node.name
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    ]


def _run_batched_full(durations: int, timeout_seconds: int) -> int:
    files = sorted((ROOT / "tests").glob("test_*.py"))
    operations: list[tuple[str, list[str]]] = []
    for path in files:
        relative = path.relative_to(ROOT)
        if path.name in NODE_ISOLATION_FILES:
            for test_name in _top_level_tests(path):
                operations.append((f"{path.name}::{test_name}", [f"{relative}::{test_name}"]))
        else:
            operations.append((path.name, [str(relative)]))

    failures: list[tuple[str, int]] = []
    for index, (label, targets) in enumerate(operations, start=1):
        print(f"\nPrueba aislada {index}/{len(operations)} · {label}", flush=True)
        arguments = ["-q", *targets]
        for target in FULL_DESELECT_BY_FILE.get(Path(targets[0].split("::", 1)[0]).name, ()):
            arguments.append(f"--deselect={target}")
        if durations > 0:
            arguments.append(f"--durations={durations}")
        result = _run(arguments, timeout_seconds)
        if result:
            failures.append((label, result))
            print(
                f"FALLO REGISTRADO · {label} · código {result}. Se continúa para completar el mapa de regresión.",
                flush=True,
            )

    if failures:
        print("\nResumen de fallos de la suite integral:", file=sys.stderr, flush=True)
        for label, result in failures:
            print(f"- {label}: código {result}", file=sys.stderr, flush=True)
        print(
            f"Suite integral completada con {len(failures)} bloque(s) fallido(s) de {len(operations)}.",
            file=sys.stderr,
            flush=True,
        )
        return 1

    print("\nSuite completa aprobada en procesos aislados.", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ejecuta una capa reproducible de pruebas.")
    parser.add_argument("tier", choices=sorted(TIERS))
    parser.add_argument("--durations", type=int, default=10)
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Límite por proceso aislado de pytest (predeterminado: 300 s).",
    )
    args = parser.parse_args()
    durations = max(0, args.durations)
    timeout_seconds = max(30, args.timeout)

    if args.tier == "full":
        return _run_batched_full(durations, timeout_seconds)

    arguments = [*TIERS[args.tier]]
    if durations > 0:
        arguments.append(f"--durations={durations}")
    return _run(arguments, timeout_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
