#!/usr/bin/env python3
"""Importa el ZIP V0.48.0 verificado sobre una copia de trabajo Git.

La fuente autocontenida se convierte en la base del repositorio. Se conservan
únicamente la infraestructura de GitHub/Codespaces y las herramientas de
migración. El comando no realiza commit ni push; esas acciones corresponden al
workflow o al operador que lo invoque.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import stat
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
VERIFIER_PATH = ROOT / "scripts" / "migration" / "verify_v048_archive.py"

PRESERVE_TOP_LEVEL = {
    ".git",
    ".github",
    ".devcontainer",
    "migration",
    ".gitignore",
    ".gitattributes",
}
PRESERVE_NESTED = {
    Path("scripts/migration"),
}


class ImportErrorV048(RuntimeError):
    """La importación no puede completarse de forma segura."""


def load_verifier():
    spec = importlib.util.spec_from_file_location("verify_v048_archive", VERIFIER_PATH)
    if not spec or not spec.loader:
        raise ImportErrorV048("No pudo cargarse el verificador V0.48")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def is_symlink(member: zipfile.ZipInfo) -> bool:
    mode = (member.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)


def extract_safely(archive_path: Path, destination: Path) -> Path:
    with zipfile.ZipFile(archive_path) as archive:
        files = [item for item in archive.infolist() if not item.is_dir()]
        if not files:
            raise ImportErrorV048("El ZIP no contiene archivos")
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            if path.is_absolute() or ".." in path.parts:
                raise ImportErrorV048(f"Ruta insegura: {item.filename}")
            if is_symlink(item):
                raise ImportErrorV048(f"No se permiten enlaces simbólicos: {item.filename}")
            target = (destination / Path(*path.parts)).resolve()
            if destination.resolve() not in target.parents and target != destination.resolve():
                raise ImportErrorV048(f"Ruta fuera del staging: {item.filename}")
        archive.extractall(destination)

    entries = [entry for entry in destination.iterdir() if entry.name != "__MACOSX"]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return destination


def backup_preserved(repo: Path, backup: Path) -> None:
    for relative in PRESERVE_NESTED:
        source = repo / relative
        if source.exists():
            target = backup / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, target)


def clear_managed_tree(repo: Path) -> None:
    for entry in repo.iterdir():
        if entry.name in PRESERVE_TOP_LEVEL:
            continue
        if entry.is_dir() and not entry.is_symlink():
            shutil.rmtree(entry)
        else:
            entry.unlink(missing_ok=True)


def copy_source(source: Path, repo: Path) -> None:
    for entry in source.iterdir():
        if entry.name in {"__MACOSX", ".git"}:
            continue
        destination = repo / entry.name
        if destination.exists():
            if destination.is_dir() and not destination.is_symlink():
                shutil.rmtree(destination)
            else:
                destination.unlink()
        if entry.is_dir() and not entry.is_symlink():
            shutil.copytree(entry, destination)
        else:
            shutil.copy2(entry, destination)


def restore_preserved(repo: Path, backup: Path) -> None:
    for relative in PRESERVE_NESTED:
        source = backup / relative
        if not source.exists():
            continue
        destination = repo / relative
        if destination.exists():
            shutil.rmtree(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, destination)


def post_import_checks(repo: Path) -> dict[str, object]:
    config = (repo / "app/config.py").read_text(encoding="utf-8")
    if "0.48.0" not in config:
        raise ImportErrorV048("La fuente importada no conserva la versión 0.48.0")
    templates = sorted((repo / "app/templates").glob("*.html"))
    tests = sorted((repo / "tests").glob("test_*.py"))
    if len(templates) != 65:
        raise ImportErrorV048(f"Se esperaban 65 plantillas; se encontraron {len(templates)}")
    if len(tests) != 31:
        raise ImportErrorV048(f"Se esperaban 31 archivos de pruebas; se encontraron {len(tests)}")
    for filename in (
        "logo-oficial.png",
        "logo-oficial-blanco.png",
        "favicon-64.png",
        "favicon-256.png",
    ):
        matches = list(repo.glob(f"**/img/brand/{filename}"))
        if not matches:
            raise ImportErrorV048(f"Falta el activo oficial después de importar: {filename}")
    return {
        "version": "0.48.0",
        "templates": len(templates),
        "test_files": len(tests),
        "github_infrastructure_preserved": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    archive = args.archive.expanduser().resolve()
    repo = args.repo.expanduser().resolve()
    if not archive.is_file() or not (repo / ".git").exists():
        print("ERROR V0.48: se requiere un ZIP existente y una copia de trabajo Git", file=sys.stderr)
        return 1

    verifier = load_verifier()
    try:
        verification = verifier.validate_archive(archive)
        with tempfile.TemporaryDirectory(prefix="cth-v048-import-") as temporary:
            temporary_root = Path(temporary)
            source = extract_safely(archive, temporary_root / "source")
            backup = temporary_root / "preserved"
            backup_preserved(repo, backup)
            clear_managed_tree(repo)
            copy_source(source, repo)
            restore_preserved(repo, backup)
        result = {"verification": verification, "import": post_import_checks(repo)}
        rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.report:
            report = args.report.expanduser().resolve()
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(rendered, encoding="utf-8")
        print(rendered, end="")
        return 0
    except Exception as exc:  # el workflow debe detenerse ante cualquier inconsistencia
        print(f"ERROR V0.48: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
