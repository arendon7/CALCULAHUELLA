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

# V1.4 intentionally replaced the historical public slogan `Mide.`. The
# equivalent diagnostic-flow regression now lives in
# test_iteration18_public_contract.py and asserts the approved V1.4 hero.
FULL_DESELECT_BY_FILE = {
    "test_app.py": (
        "tests/test_app.py::test_public_site_and_diagnostic_flow",
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

    for index, (label, targets) in enumerate(operations, start=1):
        print(f"\nPrueba aislada {index}/{len(operations)} · {label}", flush=True)
        arguments = ["-q", *targets]
        for target in FULL_DESELECT_BY_FILE.get(Path(targets[0].split("::", 1)[0]).name, ()):
            arguments.append(f"--deselect={target}")
        if durations > 0:
            arguments.append(f"--durations={durations}")
        result = _run(arguments, timeout_seconds)
        if result:
            return result
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
