#!/usr/bin/env python3
"""Importa el paquete dual V0.49.0 sobre una copia de trabajo Git.

La distribución MAC, ejecutada durante la validación original, se convierte en
el árbol runtime canónico. El núcleo compartido se verifica byte a byte contra
WINDOWS. Solo las diferencias de Windows se conservan como overlay, evitando
mantener dos copias completas del backend.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import stat
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
VERIFIER_PATH = ROOT / "scripts" / "migration" / "verify_v049_archive.py"

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
RELEASE_DOCS = {
    "00_LEEME_PRIMERO.txt",
    "MANIFIESTO_PAQUETE_V0_49_0.txt",
    "VALIDACION_V0_49.md",
    "V049_LANDING_Y_CONVERSACION_FACTORES.md",
    "PROMPTS_LANDING_V049.md",
}


class ImportErrorV049(RuntimeError):
    """La importación no puede completarse de forma segura."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_verifier():
    spec = importlib.util.spec_from_file_location(
        "verify_v049_archive", VERIFIER_PATH
    )
    if not spec or not spec.loader:
        raise ImportErrorV049("No pudo cargarse el verificador V0.49")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def is_symlink(member: zipfile.ZipInfo) -> bool:
    mode = (member.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)


def extract_safely(archive_path: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        if not any(not item.is_dir() for item in archive.infolist()):
            raise ImportErrorV049("El ZIP no contiene archivos")
        root = destination.resolve()
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            if path.is_absolute() or ".." in path.parts:
                raise ImportErrorV049(f"Ruta insegura: {item.filename}")
            if is_symlink(item):
                raise ImportErrorV049(
                    f"No se permiten enlaces simbólicos: {item.filename}"
                )
            target = (destination / Path(*path.parts)).resolve()
            if root not in target.parents and target != root:
                raise ImportErrorV049(f"Ruta fuera del staging: {item.filename}")
        archive.extractall(destination)
    return destination


def locate_package_root(extracted: Path) -> tuple[Path, str | None]:
    """Localiza MAC/ y WINDOWS/ directamente o bajo una carpeta superior."""

    if (extracted / "MAC").is_dir() and (extracted / "WINDOWS").is_dir():
        return extracted, None

    entries = [
        entry
        for entry in extracted.iterdir()
        if entry.name != "__MACOSX" and not entry.name.startswith("._")
    ]
    directories = [entry for entry in entries if entry.is_dir()]
    files = [entry for entry in entries if entry.is_file()]
    if files or len(directories) != 1:
        raise ImportErrorV049(
            "No se localizaron MAC/ y WINDOWS/ en la raíz ni dentro de una única carpeta superior"
        )

    wrapper = directories[0]
    if not (wrapper / "MAC").is_dir() or not (wrapper / "WINDOWS").is_dir():
        raise ImportErrorV049(
            f"La carpeta envolvente {wrapper.name}/ no contiene MAC/ y WINDOWS/"
        )
    return wrapper, wrapper.name


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


def copy_runtime(source: Path, repo: Path) -> None:
    if not source.is_dir():
        raise ImportErrorV049("No existe la distribución MAC extraída")
    for entry in source.iterdir():
        if entry.name in PRESERVE_TOP_LEVEL or entry.name == "__MACOSX":
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


def write_release_docs(package_root: Path, repo: Path) -> list[str]:
    destination = repo / "docs" / "releases" / "v0.49.0"
    destination.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for name in sorted(RELEASE_DOCS):
        source = package_root / name
        if not source.is_file():
            raise ImportErrorV049(f"Falta el documento de entrega {name}")
        target = destination / name
        shutil.copy2(source, target)
        copied.append(target.relative_to(repo).as_posix())
    return copied


def build_windows_overlay(
    mac_root: Path,
    windows_root: Path,
    repo: Path,
) -> dict[str, Any]:
    if not windows_root.is_dir():
        raise ImportErrorV049("No existe la distribución WINDOWS extraída")
    destination = repo / "platform" / "windows" / "overlay"
    destination.mkdir(parents=True, exist_ok=True)

    entries: list[dict[str, Any]] = []
    for source in sorted(
        path for path in windows_root.rglob("*") if path.is_file()
    ):
        relative = source.relative_to(windows_root)
        windows_data = source.read_bytes()
        mac_file = mac_root / relative
        if mac_file.is_file() and mac_file.read_bytes() == windows_data:
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(windows_data)
        entries.append(
            {
                "path": relative.as_posix(),
                "sha256": sha256_bytes(windows_data),
                "bytes": len(windows_data),
                "windows_only": not mac_file.exists(),
            }
        )

    manifest = {
        "release": "0.49.0",
        "strategy": "overlay_on_canonical_mac_runtime",
        "base": "repository root imported from MAC/",
        "files": entries,
    }
    manifest_path = repo / "platform" / "windows" / "OVERLAY_MANIFEST.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    readme = repo / "platform" / "windows" / "README.md"
    readme.write_text(
        "# Windows overlay · V0.49.0\n\n"
        "El repositorio usa el núcleo validado de `MAC/` como runtime canónico. "
        "Los archivos de esta carpeta son únicamente las diferencias necesarias "
        "para reconstruir la distribución autónoma de Windows.\n\n"
        "La ejecución física final debe probarse en Windows 10 u 11 antes de una "
        "distribución productiva.\n",
        encoding="utf-8",
    )
    return {
        "files": len(entries),
        "manifest": manifest_path.relative_to(repo).as_posix(),
    }


def post_import_checks(repo: Path) -> dict[str, Any]:
    config = (repo / "app" / "config.py").read_text(encoding="utf-8")
    if "0.49.0" not in config:
        raise ImportErrorV049(
            "La fuente importada no conserva la versión 0.49.0"
        )
    templates = sorted((repo / "app" / "templates").glob("*.html"))
    if len(templates) != 65:
        raise ImportErrorV049(
            f"Se esperaban 65 plantillas; se encontraron {len(templates)}"
        )
    for filename in (
        "logo-oficial.png",
        "logo-oficial-blanco.png",
        "favicon-64.png",
        "favicon-256.png",
    ):
        matches = list(repo.glob(f"**/img/brand/{filename}"))
        if not matches:
            raise ImportErrorV049(
                f"Falta el activo oficial después de importar: {filename}"
            )
    migrations = list(
        (repo / "migrations" / "versions").glob("*0030*.py")
    )
    if not migrations:
        raise ImportErrorV049("Falta la migración Alembic 20260804_0030")
    if not (
        repo / "platform" / "windows" / "OVERLAY_MANIFEST.json"
    ).is_file():
        raise ImportErrorV049("No se generó el overlay Windows")
    return {
        "version": "0.49.0",
        "templates": len(templates),
        "brand_assets": 4,
        "migration_0030": [path.name for path in migrations],
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
        print(
            "ERROR V0.49: se requiere un ZIP existente y una copia Git",
            file=sys.stderr,
        )
        return 1

    verifier = load_verifier()
    try:
        verification = verifier.validate_archive(archive)
        with tempfile.TemporaryDirectory(prefix="cth-v049-import-") as temporary:
            temp_root = Path(temporary)
            extracted = extract_safely(archive, temp_root / "package")
            package, package_wrapper = locate_package_root(extracted)
            mac_root = package / "MAC"
            windows_root = package / "WINDOWS"
            backup = temp_root / "preserved"
            backup_preserved(repo, backup)
            clear_managed_tree(repo)
            copy_runtime(mac_root, repo)
            restore_preserved(repo, backup)
            release_docs = write_release_docs(package, repo)
            windows_overlay = build_windows_overlay(
                mac_root, windows_root, repo
            )

        result = {
            "verification": verification,
            "import": {
                **post_import_checks(repo),
                "package_wrapper": package_wrapper,
            },
            "release_docs": release_docs,
            "windows_overlay": windows_overlay,
        }
        rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.report:
            report = args.report.expanduser().resolve()
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(rendered, encoding="utf-8")
        print(rendered, end="")
        return 0
    except Exception as exc:
        print(f"ERROR V0.49: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
