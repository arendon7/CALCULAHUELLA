#!/usr/bin/env python3
"""Importa la entrega dual definida en migration/current-release.json.

MAC se utiliza como runtime canónico y las diferencias Windows se conservan
como overlay. Importar una versión final controlada no autoriza producción
pública ni certificaciones externas.
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
VERIFIER_PATH = ROOT / "scripts" / "migration" / "verify_current_release.py"
PRESERVE_TOP_LEVEL = {
    ".git", ".github", ".devcontainer", "migration", ".gitignore", ".gitattributes",
}
PRESERVE_NESTED = {Path("scripts/migration"), Path("scripts/preview")}


class ImportReleaseError(RuntimeError):
    """La importación no puede completarse sin violar el contrato."""


def load_module():
    spec = importlib.util.spec_from_file_location(
        "verify_current_release", VERIFIER_PATH
    )
    if not spec or not spec.loader:
        raise ImportReleaseError("No pudo cargarse el verificador")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def is_symlink(item: zipfile.ZipInfo) -> bool:
    return stat.S_ISLNK((item.external_attr >> 16) & 0xFFFF)


def extract_safely(archive_path: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        root = destination.resolve()
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            if path.is_absolute() or ".." in path.parts or is_symlink(item):
                raise ImportReleaseError(f"Entrada insegura: {item.filename}")
            target = (destination / Path(*path.parts)).resolve()
            if root not in target.parents and target != root:
                raise ImportReleaseError(f"Ruta fuera del staging: {item.filename}")
        archive.extractall(destination)

    if (destination / "MAC").is_dir() and (destination / "WINDOWS").is_dir():
        return destination
    entries = [
        entry for entry in destination.iterdir()
        if entry.name != "__MACOSX" and not entry.name.startswith("._")
    ]
    if (
        len(entries) == 1
        and entries[0].is_dir()
        and (entries[0] / "MAC").is_dir()
        and (entries[0] / "WINDOWS").is_dir()
    ):
        return entries[0]
    raise ImportReleaseError("No se localizaron MAC/ y WINDOWS/")


def backup_preserved(repo: Path, backup: Path) -> None:
    for relative in PRESERVE_NESTED:
        source = repo / relative
        if source.exists():
            target = backup / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, target)


def clear_runtime(repo: Path) -> None:
    for entry in repo.iterdir():
        if entry.name in PRESERVE_TOP_LEVEL:
            continue
        if entry.is_dir() and not entry.is_symlink():
            shutil.rmtree(entry)
        else:
            entry.unlink(missing_ok=True)


def copy_tree(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise ImportReleaseError(f"No existe la distribución {source.name}")
    for entry in source.iterdir():
        if entry.name in PRESERVE_TOP_LEVEL or entry.name == "__MACOSX":
            continue
        target = destination / entry.name
        if target.exists():
            shutil.rmtree(target) if target.is_dir() else target.unlink()
        shutil.copytree(entry, target) if entry.is_dir() else shutil.copy2(entry, target)


def restore_preserved(repo: Path, backup: Path) -> None:
    for relative in PRESERVE_NESTED:
        source = backup / relative
        if source.exists():
            target = repo / relative
            if target.exists():
                shutil.rmtree(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, target)


def build_windows_overlay(
    mac: Path,
    windows: Path,
    repo: Path,
    contract: dict[str, Any],
) -> dict[str, object]:
    destination = repo / "platform" / "windows" / "overlay"
    destination.mkdir(parents=True, exist_ok=True)
    files: list[dict[str, object]] = []
    for source in sorted(path for path in windows.rglob("*") if path.is_file()):
        relative = source.relative_to(windows)
        mac_path = mac / relative
        data = source.read_bytes()
        if mac_path.is_file() and mac_path.read_bytes() == data:
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        files.append(
            {
                "path": relative.as_posix(),
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
                "windows_only": not mac_path.exists(),
            }
        )

    windows_spec = contract["distributions"]["WINDOWS"]
    manifest = {
        "release": contract["release"],
        "display_release": contract.get("display_release"),
        "strategy": "windows_overlay_on_mac_runtime",
        "canonical_runtime": "MAC",
        "controlled_deployment_authorized": contract.get(
            "controlled_deployment_authorized", False
        ),
        "public_production_authorized": contract.get(
            "public_production_authorized", False
        ),
        "production_authorized": contract.get("production_authorized", False),
        "windows_inventory_files": windows_spec.get("inventory_files"),
        "windows_tree_sha256": windows_spec.get("tree_sha256"),
        "files": files,
    }
    manifest_path = repo / "platform" / "windows" / "OVERLAY_MANIFEST.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (repo / "platform" / "windows" / "README.md").write_text(
        "# Overlay Windows\n\n"
        "El runtime raíz procede de la distribución MAC validada. Esta carpeta "
        "conserva solo las diferencias necesarias para reconstruir Windows. "
        "La prueba física en Windows 10 y Windows 11 continúa como puerta para "
        "producción pública certificada.\n",
        encoding="utf-8",
    )
    return {"files": len(files), "manifest": manifest_path.relative_to(repo).as_posix()}


def copy_release_docs(
    package: Path, repo: Path, contract: dict[str, Any]
) -> list[str]:
    slug = str(contract["release"]).replace("/", "-")
    destination = repo / "docs" / "releases" / f"v{slug}"
    destination.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for name in contract["required_documents"]:
        source = package / str(name)
        if not source.is_file():
            raise ImportReleaseError(f"Falta documento {name}")
        target = destination / source.name
        shutil.copy2(source, target)
        copied.append(target.relative_to(repo).as_posix())
    return copied


def mark_imported(repo: Path) -> dict[str, Any]:
    contract_path = repo / "migration" / "current-release.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("public_production_authorized") is True or contract.get(
        "production_authorized"
    ) is True:
        raise ImportReleaseError(
            "Una importación automática no puede autorizar producción pública"
        )
    contract["status"] = contract.get(
        "post_import_status", "runtime_imported_pending_external_certification"
    )
    evidence = contract.setdefault("source_evidence", {})
    evidence["archive_binary_received_and_verified"] = True
    evidence["archive_binary_mounted_in_current_runtime"] = False
    evidence["archive_imported_to_git"] = True
    evidence["runtime_matches_release"] = True
    contract_path.write_text(
        json.dumps(contract, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return contract


def post_checks(repo: Path, contract: dict[str, Any]) -> dict[str, object]:
    config = (repo / "app" / "config.py").read_text(encoding="utf-8")
    if str(contract["release"]).casefold() not in config.casefold():
        raise ImportReleaseError("La versión importada no coincide con el contrato")

    templates = list((repo / "app" / "templates").glob("*.html"))
    expected = int(contract["runtime_contract"]["jinja_templates"])
    if len(templates) != expected:
        raise ImportReleaseError(
            f"Plantillas importadas: {len(templates)}; esperadas {expected}"
        )

    for asset in contract["required_brand_assets"]:
        if not list((repo / "app" / "static").glob(f"**/img/brand/{asset}")):
            raise ImportReleaseError(f"Falta activo {asset}")

    validation = contract.get("validation", {})
    evidence_path = repo / str(validation.get("evidence_file", ""))
    if not evidence_path.is_file():
        raise ImportReleaseError(f"Falta la evidencia de release {evidence_path}")
    digest = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    if digest != validation.get("evidence_sha256"):
        raise ImportReleaseError(
            "La evidencia de release no coincide con su SHA-256"
        )

    overlay = repo / "platform" / "windows" / "OVERLAY_MANIFEST.json"
    if not overlay.is_file():
        raise ImportReleaseError("No se generó el overlay Windows")
    if contract.get("public_production_authorized") is not False:
        raise ImportReleaseError(
            "La versión importada debe permanecer sin autorización pública"
        )
    if contract.get("production_authorized") is not False:
        raise ImportReleaseError(
            "La versión importada debe conservar production_authorized=false"
        )

    return {
        "version": contract["release"],
        "templates": len(templates),
        "brand_assets": len(contract["required_brand_assets"]),
        "evidence_sha256": digest,
        "controlled_deployment_authorized": contract.get(
            "controlled_deployment_authorized", False
        ),
        "public_production_authorized": False,
        "production_authorized": False,
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
        print("ERROR IMPORT: se requiere ZIP y copia Git", file=sys.stderr)
        return 1

    verifier = load_module()
    contract = json.loads(
        (repo / "migration" / "current-release.json").read_text(encoding="utf-8")
    )
    try:
        verification = verifier.validate_archive(archive)
        with tempfile.TemporaryDirectory(prefix="cth-release-") as temporary:
            package = extract_safely(archive, Path(temporary) / "package")
            backup = Path(temporary) / "preserved"
            backup_preserved(repo, backup)
            clear_runtime(repo)
            copy_tree(package / "MAC", repo)
            restore_preserved(repo, backup)
            docs = copy_release_docs(package, repo, contract)
            overlay = build_windows_overlay(
                package / "MAC", package / "WINDOWS", repo, contract
            )

        imported_contract = mark_imported(repo)
        report = {
            "verification": verification,
            "import": post_checks(repo, imported_contract),
            "release_docs": docs,
            "windows_overlay": overlay,
        }
        rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(rendered, encoding="utf-8")
        print(rendered, end="")
        return 0
    except Exception as exc:
        print(f"ERROR IMPORT: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
