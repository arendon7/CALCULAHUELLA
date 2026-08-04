#!/usr/bin/env python3
"""Verifica el ZIP autocontenido V0.48.0 antes de importarlo a GitHub.

El verificador es de solo lectura. No extrae sobre el repositorio ni modifica
archivos. Exige el SHA-256 publicado y comprueba estructura, versión, activos de
marca, recursos modulares y ausencia de contenido local prohibido.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "migration" / "v0.48.0-contract.json"

FORBIDDEN_PARTS = {
    ".git",
    "__MACOSX",
    ".pytest_cache",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
}
FORBIDDEN_SUFFIXES = {
    ".db",
    ".sqlite",
    ".sqlite3",
    ".log",
    ".pyc",
    ".pyo",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
}
FORBIDDEN_EXACT = {
    ".env",
    ".env.local",
    "credentials.json",
    "secrets.json",
}


class VerificationError(RuntimeError):
    """El archivo no satisface el contrato canónico V0.48.0."""


def load_contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    members: list[zipfile.ZipInfo] = []
    for item in archive.infolist():
        if item.is_dir():
            continue
        path = PurePosixPath(item.filename)
        if path.is_absolute() or ".." in path.parts:
            raise VerificationError(f"Ruta insegura dentro del ZIP: {item.filename}")
        members.append(item)
    return members


def strip_common_root(names: list[str]) -> list[str]:
    parts = [PurePosixPath(name).parts for name in names]
    if not parts:
        return []
    first = parts[0][0] if parts[0] else ""
    if first and all(item and item[0] == first for item in parts):
        return [PurePosixPath(*item[1:]).as_posix() for item in parts]
    return [PurePosixPath(*item).as_posix() for item in parts]


def find_suffix(names: list[str], suffix: str) -> list[str]:
    normalized = suffix.lstrip("/")
    return [name for name in names if name == normalized or name.endswith("/" + normalized)]


def ensure_no_forbidden(names: list[str]) -> None:
    violations: list[str] = []
    for name in names:
        path = PurePosixPath(name)
        if any(part in FORBIDDEN_PARTS for part in path.parts):
            violations.append(name)
            continue
        if path.name in FORBIDDEN_EXACT or path.suffix.lower() in FORBIDDEN_SUFFIXES:
            violations.append(name)
            continue
        lowered = name.casefold()
        if any(segment in lowered for segment in ("/evidencias/", "/backups/", "/certificados/")):
            violations.append(name)
    if violations:
        sample = "\n  - ".join(violations[:20])
        raise VerificationError(f"Contenido prohibido detectado:\n  - {sample}")


def read_text_by_suffix(
    archive: zipfile.ZipFile,
    members: list[zipfile.ZipInfo],
    stripped_names: list[str],
    suffix: str,
) -> str:
    matches = [index for index, name in enumerate(stripped_names) if name == suffix or name.endswith("/" + suffix)]
    if len(matches) != 1:
        raise VerificationError(f"Se esperaba exactamente un archivo {suffix}; encontrados: {len(matches)}")
    return archive.read(members[matches[0]]).decode("utf-8")


def validate_archive(path: Path) -> dict[str, Any]:
    contract = load_contract()
    expected_archive = contract["archive"]
    actual_hash = sha256(path)
    if actual_hash != expected_archive["sha256"]:
        raise VerificationError(
            "SHA-256 del ZIP distinto del publicado. "
            f"Esperado {expected_archive['sha256']}; obtenido {actual_hash}."
        )

    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise VerificationError("El archivo no es un ZIP válido") from exc

    with archive:
        members = safe_members(archive)
        stripped = strip_common_root([item.filename for item in members])
        ensure_no_forbidden(stripped)

        required_source = (
            "app/main.py",
            "app/config.py",
            "alembic.ini",
            "run.py",
            "requirements.txt",
        )
        for required in required_source:
            if not find_suffix(stripped, required):
                raise VerificationError(f"Falta el archivo fuente requerido: {required}")

        config = read_text_by_suffix(archive, members, stripped, "app/config.py")
        version_patterns = (
            r'version\s*:\s*str\s*=\s*["\']0\.48\.0["\']',
            r'VERSION\s*=\s*["\']0\.48\.0["\']',
        )
        if not any(re.search(pattern, config) for pattern in version_patterns):
            raise VerificationError("app/config.py no declara la versión 0.48.0")

        template_names = [
            name for name in stripped if name.startswith("app/templates/") and name.endswith(".html")
        ]
        expected_templates = int(contract["source_tree"]["jinja_templates"])
        if len(template_names) != expected_templates:
            raise VerificationError(
                f"Plantillas Jinja: esperadas {expected_templates}; encontradas {len(template_names)}"
            )

        test_names = [
            name for name in stripped if name.startswith("tests/test_") and name.endswith(".py")
        ]
        expected_tests = int(contract["source_tree"]["test_files"])
        if len(test_names) != expected_tests:
            raise VerificationError(
                f"Archivos de pruebas: esperados {expected_tests}; encontrados {len(test_names)}"
            )

        for asset in contract["required_brand_assets"]:
            if not any(name.endswith("/img/brand/" + asset) for name in stripped):
                raise VerificationError(f"Falta el activo oficial de marca: {asset}")

        module_pngs = [
            name for name in stripped if "/img/modules/" in ("/" + name) and name.endswith(".png")
        ]
        if len(module_pngs) < int(contract["minimum_module_pngs"]):
            raise VerificationError(
                f"Se esperaban al menos {contract['minimum_module_pngs']} imágenes modulares; "
                f"se encontraron {len(module_pngs)}"
            )
        for asset in contract["required_module_assets"]:
            if not any(name.endswith("/img/modules/" + asset) for name in stripped):
                raise VerificationError(f"Falta la imagen modular requerida: {asset}")

        manifests = [name for name in stripped if name.endswith("MANIFIESTO_V0_48_0.txt")]
        if len(manifests) != 1:
            raise VerificationError("Falta MANIFIESTO_V0_48_0.txt o aparece duplicado")
        manifest = read_text_by_suffix(archive, members, stripped, manifests[0])
        logical_hash = contract["source_tree"]["logical_sha256"]
        required_manifest_tokens = (
            "Versión de aplicación: 0.48.0",
            "406 archivos funcionales",
            logical_hash,
        )
        for token in required_manifest_tokens:
            if token not in manifest:
                raise VerificationError(f"El manifiesto no contiene la evidencia requerida: {token}")

        return {
            "status": "verified_exact_archive",
            "archive": path.name,
            "sha256": actual_hash,
            "files_in_zip": len(stripped),
            "jinja_templates": len(template_names),
            "test_files": len(test_names),
            "brand_assets": sorted(contract["required_brand_assets"]),
            "module_pngs": len(module_pngs),
            "logical_tree_sha256_declared": logical_hash,
            "safe_to_stage": True,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    path = args.archive.expanduser().resolve()
    if not path.is_file():
        print(f"ERROR V0.48: no existe {path}", file=sys.stderr)
        return 1
    try:
        report = validate_archive(path)
    except (VerificationError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"ERROR V0.48: {exc}", file=sys.stderr)
        return 1
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
