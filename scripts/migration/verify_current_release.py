#!/usr/bin/env python3
"""Verifica el paquete dual definido en migration/current-release.json."""

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
CONTRACT_PATH = ROOT / "migration" / "current-release.json"
FORBIDDEN_PARTS = {".git", "__MACOSX", ".pytest_cache", "__pycache__", ".venv", "venv", "node_modules"}
FORBIDDEN_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".log", ".pyc", ".pem", ".key", ".p12", ".pfx"}
FORBIDDEN_EXACT = {".env", ".env.local", "credentials.json", "secrets.json"}
CORE_PREFIXES = ("app/", "migrations/", "tests/")
CORE_FILES = {"alembic.ini", "Dockerfile", "requirements.txt", "requirements-dev.txt", "requirements-prod.txt", "run.py", "start_prod.sh"}


class ReleaseError(RuntimeError):
    pass


def load_contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_members(archive: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    result: dict[str, zipfile.ZipInfo] = {}
    for item in archive.infolist():
        if item.is_dir():
            continue
        path = PurePosixPath(item.filename)
        if path.is_absolute() or ".." in path.parts:
            raise ReleaseError(f"Ruta insegura: {item.filename}")
        name = path.as_posix().lstrip("./")
        if name in result:
            raise ReleaseError(f"Ruta duplicada: {name}")
        result[name] = item
    if not result:
        raise ReleaseError("El ZIP está vacío")
    return result


def normalize_layout(members: dict[str, zipfile.ZipInfo]) -> tuple[dict[str, zipfile.ZipInfo], str | None]:
    names = list(members)
    if any(name.startswith("MAC/") for name in names) and any(name.startswith("WINDOWS/") for name in names):
        return members, None
    top = {PurePosixPath(name).parts[0] for name in names}
    if len(top) != 1:
        raise ReleaseError("No se localizaron MAC/ y WINDOWS/")
    wrapper = next(iter(top))
    prefix = wrapper + "/"
    stripped = {name[len(prefix):]: item for name, item in members.items() if name.startswith(prefix) and name[len(prefix):]}
    if not any(name.startswith("MAC/") for name in stripped) or not any(name.startswith("WINDOWS/") for name in stripped):
        raise ReleaseError(f"{wrapper}/ no contiene MAC/ y WINDOWS/")
    return stripped, wrapper


def ensure_clean(names: list[str]) -> None:
    violations: list[str] = []
    for name in names:
        path = PurePosixPath(name)
        if any(part in FORBIDDEN_PARTS for part in path.parts) or path.name in FORBIDDEN_EXACT or path.suffix.lower() in FORBIDDEN_SUFFIXES:
            violations.append(name)
        lowered = f"/{name.casefold()}/"
        if any(token in lowered for token in ("/evidencias/", "/backups/", "/certificados/")):
            violations.append(name)
    if violations:
        raise ReleaseError("Contenido prohibido: " + ", ".join(sorted(set(violations))[:20]))


def distribution(members: dict[str, zipfile.ZipInfo], root: str) -> dict[str, zipfile.ZipInfo]:
    prefix = root + "/"
    return {name[len(prefix):]: item for name, item in members.items() if name.startswith(prefix)}


def read_text(archive: zipfile.ZipFile, mapping: dict[str, zipfile.ZipInfo], name: str) -> str:
    if name not in mapping:
        raise ReleaseError(f"Falta {name}")
    return archive.read(mapping[name]).decode("utf-8")


def validate_distribution(archive: zipfile.ZipFile, name: str, mapping: dict[str, zipfile.ZipInfo], contract: dict[str, Any]) -> dict[str, Any]:
    for required in ("app/main.py", "app/config.py", "migrations/env.py", "alembic.ini", "run.py", "requirements.txt"):
        if required not in mapping:
            raise ReleaseError(f"{name}: falta {required}")
    release = contract["release"]
    config = read_text(archive, mapping, "app/config.py")
    if release not in config:
        raise ReleaseError(f"{name}: app/config.py no declara {release}")
    templates = [path for path in mapping if path.startswith("app/templates/") and path.endswith(".html")]
    expected_templates = int(contract["runtime_contract"]["jinja_templates"])
    if len(templates) != expected_templates:
        raise ReleaseError(f"{name}: {len(templates)} plantillas; se esperaban {expected_templates}")
    for asset in contract["required_brand_assets"]:
        if not any(path.endswith("/img/brand/" + asset) for path in mapping):
            raise ReleaseError(f"{name}: falta {asset}")
    minimum = int(contract["distributions"][name]["functional_files"])
    if len(mapping) < minimum:
        raise ReleaseError(f"{name}: solo {len(mapping)} archivos; mínimo documentado {minimum}")
    head = str(contract["runtime_contract"]["alembic_head"])
    if not any(head in path or head in archive.read(item).decode("utf-8", errors="ignore") for path, item in mapping.items() if path.startswith("migrations/versions/") and path.endswith(".py")):
        raise ReleaseError(f"{name}: no se encontró Alembic {head}")
    return {"files": len(mapping), "templates": len(templates)}


def compare_core(archive: zipfile.ZipFile, mac: dict[str, zipfile.ZipInfo], windows: dict[str, zipfile.ZipInfo]) -> dict[str, Any]:
    def hashes(mapping: dict[str, zipfile.ZipInfo]) -> dict[str, str]:
        return {path: sha256_bytes(archive.read(item)) for path, item in mapping.items() if path in CORE_FILES or path.startswith(CORE_PREFIXES)}
    left, right = hashes(mac), hashes(windows)
    changed = sorted(path for path in set(left) & set(right) if left[path] != right[path])
    missing = sorted(set(left) ^ set(right))
    if changed or missing:
        raise ReleaseError(f"Núcleo MAC/WINDOWS divergente: changed={changed[:10]} missing={missing[:10]}")
    return {"shared_files": len(left)}


def validate_archive(path: Path) -> dict[str, Any]:
    contract = load_contract()
    if path.name != contract["archive"]["filename"]:
        raise ReleaseError(f"Nombre esperado: {contract['archive']['filename']}")
    actual = sha256_file(path)
    if actual != contract["archive"]["sha256"]:
        raise ReleaseError(f"SHA-256 distinto: {actual}")
    with zipfile.ZipFile(path) as archive:
        members, wrapper = normalize_layout(safe_members(archive))
        ensure_clean(list(members))
        for document in contract["required_documents"]:
            if document not in members:
                raise ReleaseError(f"Falta documento raíz {document}")
        manifest = read_text(archive, members, "MANIFIESTO_PAQUETE_V0_52_0.txt")
        required_tokens = [
            contract["release"],
            str(contract["runtime_contract"]["routes"]),
            str(contract["runtime_contract"]["jinja_templates"]),
            str(contract["runtime_contract"]["orm_models"]),
            str(contract["runtime_contract"]["physical_tables_after_migration"]),
            str(contract["runtime_contract"]["alembic_head"]),
            contract["distributions"]["MAC"]["tree_sha256"],
            contract["distributions"]["WINDOWS"]["tree_sha256"],
        ]
        for token in required_tokens:
            if token not in manifest:
                raise ReleaseError(f"El manifiesto no contiene {token}")
        mac = distribution(members, "MAC")
        windows = distribution(members, "WINDOWS")
        return {
            "status": "verified_current_release",
            "release": contract["release"],
            "archive": path.name,
            "sha256": actual,
            "wrapper": wrapper,
            "mac": validate_distribution(archive, "MAC", mac, contract),
            "windows": validate_distribution(archive, "WINDOWS", windows, contract),
            "core": compare_core(archive, mac, windows),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    try:
        report = validate_archive(args.archive.expanduser().resolve())
    except (ReleaseError, OSError, UnicodeError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(f"ERROR RELEASE: {exc}", file=sys.stderr)
        return 1
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
