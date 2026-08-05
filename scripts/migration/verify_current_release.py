#!/usr/bin/env python3
"""Verifica el paquete dual definido en migration/current-release.json.

La entrega final puede acreditar métricas en su documento de validación y la
integridad física mediante un manifiesto por archivo. El verificador acepta esa
separación y comprueba realmente tamaño y SHA-256 de cada entrada inventariada.
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
CONTRACT_PATH = ROOT / "migration" / "current-release.json"
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
CORE_PREFIXES = ("app/", "migrations/", "tests/")
CORE_FILES = {
    "alembic.ini",
    "Dockerfile",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-prod.txt",
    "run.py",
    "start_prod.sh",
}
INVENTORY_LINE = re.compile(
    r"^(?P<path>.+?)\s*\|\s*(?P<bytes>\d+)\s*\|\s*"
    r"(?P<sha>[0-9a-fA-F]{64})\s*$"
)


class ReleaseError(RuntimeError):
    """La entrega no satisface el contrato canónico activo."""


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


def normalize_layout(
    members: dict[str, zipfile.ZipInfo],
) -> tuple[dict[str, zipfile.ZipInfo], str | None]:
    names = list(members)
    if any(name.startswith("MAC/") for name in names) and any(
        name.startswith("WINDOWS/") for name in names
    ):
        return members, None

    top = {PurePosixPath(name).parts[0] for name in names}
    if len(top) != 1:
        raise ReleaseError("No se localizaron MAC/ y WINDOWS/")
    wrapper = next(iter(top))
    prefix = wrapper + "/"
    stripped = {
        name[len(prefix) :]: item
        for name, item in members.items()
        if name.startswith(prefix) and name[len(prefix) :]
    }
    if not any(name.startswith("MAC/") for name in stripped) or not any(
        name.startswith("WINDOWS/") for name in stripped
    ):
        raise ReleaseError(f"{wrapper}/ no contiene MAC/ y WINDOWS/")
    return stripped, wrapper


def ensure_clean(names: list[str]) -> None:
    violations: list[str] = []
    for name in names:
        path = PurePosixPath(name)
        if (
            any(part in FORBIDDEN_PARTS for part in path.parts)
            or path.name in FORBIDDEN_EXACT
            or path.suffix.lower() in FORBIDDEN_SUFFIXES
        ):
            violations.append(name)
        lowered = f"/{name.casefold()}/"
        if any(
            token in lowered
            for token in ("/evidencias/", "/backups/", "/certificados/")
        ):
            violations.append(name)
    if violations:
        raise ReleaseError(
            "Contenido prohibido: "
            + ", ".join(sorted(set(violations))[:20])
        )


def distribution(
    members: dict[str, zipfile.ZipInfo], root: str
) -> dict[str, zipfile.ZipInfo]:
    prefix = root + "/"
    return {
        name[len(prefix) :]: item
        for name, item in members.items()
        if name.startswith(prefix)
    }


def read_text(
    archive: zipfile.ZipFile,
    mapping: dict[str, zipfile.ZipInfo],
    name: str,
) -> str:
    if name not in mapping:
        raise ReleaseError(f"Falta {name}")
    return archive.read(mapping[name]).decode("utf-8")


def required_document_by_prefix(
    contract: dict[str, Any], prefix: str
) -> str:
    candidates = [
        str(name)
        for name in contract.get("required_documents", [])
        if Path(str(name)).name.upper().startswith(prefix.upper())
    ]
    if len(candidates) != 1:
        raise ReleaseError(
            f"El contrato debe declarar exactamente un documento {prefix}"
        )
    return candidates[0]


def metric_pattern(labels: tuple[str, ...], value: int) -> str:
    label = "(?:" + "|".join(labels) + ")"
    separator = r"\s*(?::|·|-)?\s*"
    return rf"(?:\b{label}{separator}{value}\b|\b{value}{separator}{label}\b)"


def validate_release_summary(text: str, contract: dict[str, Any]) -> None:
    runtime = contract["runtime_contract"]
    release = str(contract["release"])
    display = str(contract.get("display_release", release))
    release_patterns = {
        re.escape(release).replace(r"\-", "[-–—]"),
        re.escape(display).replace(r"\-", "[-–—]"),
    }
    if not any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in release_patterns
    ):
        raise ReleaseError("La validación no acredita la versión objetivo")

    metrics = {
        "routes": metric_pattern((r"rutas?(?:\s+FastAPI)?",), int(runtime["routes"])),
        "templates": metric_pattern(
            (r"plantillas?(?:\s+(?:HTML|Jinja))?",),
            int(runtime["jinja_templates"]),
        ),
        "models": metric_pattern(
            (r"modelos?(?:\s+ORM)?",), int(runtime["orm_models"])
        ),
        "tables": metric_pattern(
            (r"tablas?(?:\s+físicas?)?(?:\s+desde\s+base\s+vacía)?",),
            int(runtime["physical_tables_after_migration"]),
        ),
    }
    for label, pattern in metrics.items():
        if not re.search(pattern, text, re.IGNORECASE):
            raise ReleaseError(
                f"La validación no acredita la métrica etiquetada: {label}"
            )

    if str(runtime["alembic_head"]) not in text:
        raise ReleaseError("La validación no acredita la cabeza Alembic")

    expected_tests = contract.get("validation", {}).get("suite_tests_passed")
    if expected_tests is not None and not re.search(
        metric_pattern((r"pruebas?",), int(expected_tests)),
        text,
        re.IGNORECASE,
    ):
        raise ReleaseError("La validación no acredita la suite documentada")


def parse_inventory(manifest: str) -> dict[str, tuple[int, str]]:
    inventory: dict[str, tuple[int, str]] = {}
    for raw_line in manifest.splitlines():
        match = INVENTORY_LINE.match(raw_line.strip())
        if not match:
            continue
        path = PurePosixPath(match.group("path").strip()).as_posix().lstrip("./")
        if path in inventory:
            raise ReleaseError(f"Ruta repetida en manifiesto: {path}")
        inventory[path] = (
            int(match.group("bytes")),
            match.group("sha").lower(),
        )
    if not inventory:
        raise ReleaseError("El manifiesto no contiene inventario SHA-256")
    return inventory


def validate_manifest_header(manifest: str, contract: dict[str, Any]) -> None:
    release = str(contract.get("display_release", contract["release"]))
    normalized = re.escape(release).replace(r"\-", "[-–—]")
    if not re.search(normalized, manifest, re.IGNORECASE):
        raise ReleaseError("El manifiesto no acredita la versión objetivo")

    total = contract.get("archive", {}).get("inventory_total_files")
    if total is not None and not re.search(
        metric_pattern((r"archivos?\s+inventariados?",), int(total)),
        manifest,
        re.IGNORECASE,
    ):
        raise ReleaseError("El manifiesto no acredita el total inventariado")

    for name in ("MAC", "WINDOWS"):
        expected = contract["distributions"][name].get("inventory_files")
        if expected is None:
            continue
        pattern = rf"\b{name}\s*:\s*{int(expected)}\b"
        if not re.search(pattern, manifest, re.IGNORECASE):
            raise ReleaseError(
                f"El manifiesto no acredita el inventario {name}"
            )

    if "despliegue controlado" not in manifest.casefold():
        raise ReleaseError(
            "El manifiesto no conserva la clasificación de despliegue controlado"
        )


def validate_inventory_entries(
    archive: zipfile.ZipFile,
    members: dict[str, zipfile.ZipInfo],
    inventory: dict[str, tuple[int, str]],
    contract: dict[str, Any],
) -> dict[str, Any]:
    missing: list[str] = []
    mismatched: list[str] = []
    verified = 0
    for path, (expected_size, expected_hash) in inventory.items():
        item = members.get(path)
        if item is None:
            missing.append(path)
            continue
        data = archive.read(item)
        if len(data) != expected_size or sha256_bytes(data) != expected_hash:
            mismatched.append(path)
            continue
        verified += 1

    if missing or mismatched:
        raise ReleaseError(
            "Inventario físico inválido: "
            f"faltantes={missing[:10]} distintos={mismatched[:10]}"
        )

    for document in contract["required_documents"]:
        if document not in inventory:
            raise ReleaseError(
                f"El manifiesto no inventaría el documento requerido {document}"
            )

    evidence_file = contract.get("validation", {}).get("evidence_file")
    evidence_hash = contract.get("validation", {}).get("evidence_sha256")
    if evidence_file and evidence_hash:
        for root in ("MAC", "WINDOWS"):
            path = f"{root}/{evidence_file}"
            entry = inventory.get(path)
            if entry is None or entry[1] != str(evidence_hash):
                raise ReleaseError(
                    f"El manifiesto no acredita la evidencia final en {root}"
                )

    expected_minimum = sum(
        int(values.get("inventory_files", 0))
        for values in contract["distributions"].values()
    )
    if verified < expected_minimum:
        raise ReleaseError(
            f"Inventario verificado insuficiente: {verified} < {expected_minimum}"
        )
    return {
        "entries": len(inventory),
        "verified_entries": verified,
        "missing_entries": 0,
        "mismatched_entries": 0,
    }


def validate_distribution(
    archive: zipfile.ZipFile,
    name: str,
    mapping: dict[str, zipfile.ZipInfo],
    contract: dict[str, Any],
) -> dict[str, Any]:
    for required in (
        "app/main.py",
        "app/config.py",
        "migrations/env.py",
        "alembic.ini",
        "run.py",
        "requirements.txt",
    ):
        if required not in mapping:
            raise ReleaseError(f"{name}: falta {required}")

    release = str(contract["release"])
    config = read_text(archive, mapping, "app/config.py")
    if release.casefold() not in config.casefold():
        raise ReleaseError(f"{name}: app/config.py no declara {release}")

    templates = [
        path
        for path in mapping
        if path.startswith("app/templates/") and path.endswith(".html")
    ]
    expected_templates = int(contract["runtime_contract"]["jinja_templates"])
    if len(templates) != expected_templates:
        raise ReleaseError(
            f"{name}: {len(templates)} plantillas; "
            f"se esperaban {expected_templates}"
        )

    for asset in contract["required_brand_assets"]:
        if not any(path.endswith("/img/brand/" + asset) for path in mapping):
            raise ReleaseError(f"{name}: falta {asset}")

    distribution_contract = contract["distributions"][name]
    minimum = int(
        distribution_contract.get(
            "minimum_files",
            distribution_contract.get("functional_files", 0),
        )
    )
    exact = distribution_contract.get("inventory_files")
    if len(mapping) < minimum:
        raise ReleaseError(
            f"{name}: solo {len(mapping)} archivos; mínimo {minimum}"
        )
    if exact is not None and len(mapping) != int(exact):
        raise ReleaseError(
            f"{name}: {len(mapping)} archivos; inventario esperado {exact}"
        )

    head = str(contract["runtime_contract"]["alembic_head"])
    migration_files = [
        (path, item)
        for path, item in mapping.items()
        if path.startswith("migrations/versions/") and path.endswith(".py")
    ]
    if not any(
        head in path
        or head in archive.read(item).decode("utf-8", errors="ignore")
        for path, item in migration_files
    ):
        raise ReleaseError(f"{name}: no se encontró Alembic {head}")

    evidence_file = contract.get("validation", {}).get("evidence_file")
    if evidence_file and str(evidence_file) not in mapping:
        raise ReleaseError(f"{name}: falta la evidencia {evidence_file}")

    return {"files": len(mapping), "templates": len(templates)}


def compare_core(
    archive: zipfile.ZipFile,
    mac: dict[str, zipfile.ZipInfo],
    windows: dict[str, zipfile.ZipInfo],
) -> dict[str, Any]:
    def hashes(mapping: dict[str, zipfile.ZipInfo]) -> dict[str, str]:
        return {
            path: sha256_bytes(archive.read(item))
            for path, item in mapping.items()
            if path in CORE_FILES or path.startswith(CORE_PREFIXES)
        }

    left = hashes(mac)
    right = hashes(windows)
    changed = sorted(
        path
        for path in set(left) & set(right)
        if left[path] != right[path]
    )
    missing = sorted(set(left) ^ set(right))
    if changed or missing:
        raise ReleaseError(
            "Núcleo MAC/WINDOWS divergente: "
            f"changed={changed[:10]} missing={missing[:10]}"
        )
    return {"shared_files": len(left)}


def validate_archive(path: Path) -> dict[str, Any]:
    contract = load_contract()
    expected_archive = contract["archive"]
    if path.name != expected_archive["filename"]:
        raise ReleaseError(f"Nombre esperado: {expected_archive['filename']}")

    actual = sha256_file(path)
    if actual != expected_archive["sha256"]:
        raise ReleaseError(f"SHA-256 distinto: {actual}")

    with zipfile.ZipFile(path) as archive:
        members, wrapper = normalize_layout(safe_members(archive))
        ensure_clean(list(members))
        for document in contract["required_documents"]:
            if document not in members:
                raise ReleaseError(f"Falta documento raíz {document}")

        manifest_name = required_document_by_prefix(contract, "MANIFIESTO")
        validation_name = required_document_by_prefix(contract, "VALIDACION")
        manifest = read_text(archive, members, manifest_name)
        validation = read_text(archive, members, validation_name)
        validate_manifest_header(manifest, contract)
        validate_release_summary(validation, contract)
        inventory = parse_inventory(manifest)
        inventory_report = validate_inventory_entries(
            archive, members, inventory, contract
        )

        mac = distribution(members, "MAC")
        windows = distribution(members, "WINDOWS")
        return {
            "status": "verified_current_release",
            "release": contract["release"],
            "archive": path.name,
            "sha256": actual,
            "wrapper": wrapper,
            "manifest": manifest_name,
            "validation": validation_name,
            "inventory": inventory_report,
            "mac": validate_distribution(archive, "MAC", mac, contract),
            "windows": validate_distribution(
                archive, "WINDOWS", windows, contract
            ),
            "core": compare_core(archive, mac, windows),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    try:
        report = validate_archive(args.archive.expanduser().resolve())
    except (
        ReleaseError,
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        zipfile.BadZipFile,
    ) as exc:
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
