#!/usr/bin/env python3
"""Verifica el paquete dual V0.49.0 antes de importarlo a GitHub.

La validación es de solo lectura. Exige el SHA-256 publicado, las distribuciones
MAC y WINDOWS, paridad del núcleo compartido, activos visuales exactos y ausencia
de datos locales o secretos. Acepta que el ZIP contenga directamente la entrega
o que esté envuelta en una única carpeta superior.
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
CONTRACT_PATH = ROOT / "migration" / "v0.49.0-contract.json"

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

# El núcleo funcional debe ser idéntico. Los scripts de instalación y ciclo de
# vida son deliberadamente distintos por plataforma y se conservan en overlay.
SHARED_CORE_PREFIXES = (
    "app/",
    "migrations/",
    "tests/",
)
SHARED_CORE_FILES = {
    "alembic.ini",
    "Dockerfile",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-prod.txt",
    "run.py",
    "start_prod.sh",
}


class VerificationError(RuntimeError):
    """El ZIP no satisface el contrato canónico V0.49.0."""


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


def normalize_member(name: str) -> str:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise VerificationError(f"Ruta insegura dentro del ZIP: {name}")
    normalized = path.as_posix().lstrip("./")
    if not normalized:
        raise VerificationError("El ZIP contiene una ruta vacía")
    return normalized


def safe_members(archive: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    members: dict[str, zipfile.ZipInfo] = {}
    for item in archive.infolist():
        if item.is_dir():
            continue
        normalized = normalize_member(item.filename)
        if normalized in members:
            raise VerificationError(f"Ruta duplicada dentro del ZIP: {normalized}")
        members[normalized] = item
    if not members:
        raise VerificationError("El ZIP no contiene archivos")
    return members


def normalize_package_layout(
    members: dict[str, zipfile.ZipInfo],
) -> tuple[dict[str, zipfile.ZipInfo], str | None]:
    """Retira una única carpeta envolvente cuando contiene toda la entrega."""

    names = sorted(members)
    if any(name.startswith("MAC/") for name in names) and any(
        name.startswith("WINDOWS/") for name in names
    ):
        return members, None

    top_levels = {PurePosixPath(name).parts[0] for name in names}
    if len(top_levels) != 1:
        raise VerificationError(
            "No se localizaron MAC/ y WINDOWS/ en la raíz ni dentro de una única carpeta superior"
        )

    wrapper = next(iter(top_levels))
    prefix = wrapper + "/"
    stripped: dict[str, zipfile.ZipInfo] = {}
    for name, item in members.items():
        if not name.startswith(prefix):
            raise VerificationError("La carpeta envolvente no contiene todos los archivos")
        relative = name[len(prefix) :]
        if not relative:
            continue
        if relative in stripped:
            raise VerificationError(f"Ruta duplicada después de retirar {wrapper}/: {relative}")
        stripped[relative] = item

    stripped_names = sorted(stripped)
    if not any(name.startswith("MAC/") for name in stripped_names) or not any(
        name.startswith("WINDOWS/") for name in stripped_names
    ):
        raise VerificationError(
            f"La carpeta envolvente {wrapper}/ no contiene las distribuciones MAC/ y WINDOWS/"
        )
    return stripped, wrapper


def ensure_no_forbidden(names: list[str]) -> None:
    violations: list[str] = []
    for name in names:
        path = PurePosixPath(name)
        if any(part in FORBIDDEN_PARTS for part in path.parts):
            violations.append(name)
            continue
        if path.name in FORBIDDEN_EXACT or path.suffix.casefold() in FORBIDDEN_SUFFIXES:
            violations.append(name)
            continue
        lowered = f"/{name.casefold()}/"
        if any(
            segment in lowered
            for segment in ("/evidencias/", "/backups/", "/certificados/")
        ):
            violations.append(name)
    if violations:
        sample = "\n  - ".join(violations[:25])
        raise VerificationError(f"Contenido prohibido detectado:\n  - {sample}")


def read_member_text(
    archive: zipfile.ZipFile,
    members: dict[str, zipfile.ZipInfo],
    name: str,
) -> str:
    if name not in members:
        raise VerificationError(f"Falta el archivo requerido: {name}")
    try:
        return archive.read(members[name]).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VerificationError(f"El archivo no es UTF-8: {name}") from exc


def distribution_member_map(
    members: dict[str, zipfile.ZipInfo], root: str
) -> dict[str, zipfile.ZipInfo]:
    prefix = root.rstrip("/") + "/"
    return {
        name[len(prefix) :]: item
        for name, item in members.items()
        if name.startswith(prefix)
    }


def require_distribution_structure(
    archive: zipfile.ZipFile,
    distribution: str,
    mapping: dict[str, zipfile.ZipInfo],
    contract: dict[str, Any],
) -> dict[str, Any]:
    required_source = (
        "app/main.py",
        "app/config.py",
        "alembic.ini",
        "run.py",
        "requirements.txt",
        "migrations/env.py",
    )
    for required in required_source:
        if required not in mapping:
            raise VerificationError(f"{distribution}: falta {required}")

    config = archive.read(mapping["app/config.py"]).decode("utf-8")
    if not re.search(r'version\s*:\s*str\s*=\s*["\']0\.49\.0["\']', config):
        raise VerificationError(f"{distribution}: app/config.py no declara 0.49.0")

    template_names = sorted(
        name
        for name in mapping
        if name.startswith("app/templates/") and name.endswith(".html")
    )
    expected_templates = int(contract["runtime"]["jinja_templates"])
    if len(template_names) != expected_templates:
        raise VerificationError(
            f"{distribution}: plantillas esperadas {expected_templates}; encontradas {len(template_names)}"
        )

    for asset in contract["required_brand_assets"]:
        candidates = [
            name for name in mapping if name.endswith("/img/brand/" + asset)
        ]
        if len(candidates) != 1:
            raise VerificationError(
                f"{distribution}: se esperaba un único activo {asset}; encontrados {len(candidates)}"
            )

    module_pngs = sorted(
        name
        for name in mapping
        if "/img/modules/" in ("/" + name) and name.endswith(".png")
    )
    if len(module_pngs) < int(contract["minimum_module_pngs"]):
        raise VerificationError(
            f"{distribution}: se esperaban al menos {contract['minimum_module_pngs']} imágenes modulares; "
            f"se encontraron {len(module_pngs)}"
        )
    for asset in contract["required_module_assets"]:
        if not any(name.endswith("/img/modules/" + asset) for name in mapping):
            raise VerificationError(f"{distribution}: falta la imagen modular {asset}")

    migration_tokens = [
        name
        for name in mapping
        if name.startswith("migrations/versions/")
        and "0030" in PurePosixPath(name).name
    ]
    if not migration_tokens:
        raise VerificationError(
            f"{distribution}: no se encontró la migración Alembic 20260804_0030"
        )

    landing_text = "\n".join(
        archive.read(mapping[name]).decode("utf-8", errors="ignore")
        for name in template_names
    )
    required_landing_tokens = (
        "Potenciado por Greenatics",
        "Huella Esencial",
        "Gestión de Carbono",
        "Gestión Avanzada",
    )
    for token in required_landing_tokens:
        if token not in landing_text:
            raise VerificationError(f"{distribution}: la landing no contiene {token!r}")

    python_text = "\n".join(
        archive.read(mapping[name]).decode("utf-8", errors="ignore")
        for name in mapping
        if name.startswith("app/") and name.endswith(".py")
    )
    all_paths = "\n".join(mapping)
    for token in (
        "ActivityFactorSelection",
        "activity_factor_selections",
        "20260804_0030",
    ):
        if token not in python_text and token not in all_paths:
            raise VerificationError(f"{distribution}: falta la capacidad técnica {token}")

    return {
        "physical_files": len(mapping),
        "templates": len(template_names),
        "module_pngs": len(module_pngs),
        "migration_0030_files": migration_tokens,
    }


def shared_core_hashes(
    archive: zipfile.ZipFile,
    mapping: dict[str, zipfile.ZipInfo],
) -> dict[str, str]:
    selected: dict[str, str] = {}
    for name, item in mapping.items():
        if name in SHARED_CORE_FILES or name.startswith(SHARED_CORE_PREFIXES):
            selected[name] = sha256_bytes(archive.read(item))
    return selected


def compare_shared_core(
    archive: zipfile.ZipFile,
    mac: dict[str, zipfile.ZipInfo],
    windows: dict[str, zipfile.ZipInfo],
) -> dict[str, Any]:
    mac_hashes = shared_core_hashes(archive, mac)
    windows_hashes = shared_core_hashes(archive, windows)
    mac_only = sorted(set(mac_hashes) - set(windows_hashes))
    windows_only = sorted(set(windows_hashes) - set(mac_hashes))
    changed = sorted(
        name
        for name in set(mac_hashes) & set(windows_hashes)
        if mac_hashes[name] != windows_hashes[name]
    )
    if mac_only or windows_only or changed:
        details = {
            "mac_only": mac_only[:20],
            "windows_only": windows_only[:20],
            "changed": changed[:20],
        }
        raise VerificationError(
            "El núcleo compartido MAC/WINDOWS no es idéntico: "
            + json.dumps(details, ensure_ascii=False)
        )
    return {
        "shared_files": len(mac_hashes),
        "shared_core_sha256": sha256_bytes(
            "\n".join(
                f"{name}:{mac_hashes[name]}" for name in sorted(mac_hashes)
            ).encode("utf-8")
        ),
    }


def windows_overlay_entries(
    archive: zipfile.ZipFile,
    mac: dict[str, zipfile.ZipInfo],
    windows: dict[str, zipfile.ZipInfo],
) -> list[dict[str, Any]]:
    overlay: list[dict[str, Any]] = []
    for name, item in sorted(windows.items()):
        data = archive.read(item)
        mac_item = mac.get(name)
        if mac_item is not None and archive.read(mac_item) == data:
            continue
        overlay.append(
            {
                "path": name,
                "sha256": sha256_bytes(data),
                "bytes": len(data),
                "windows_only": mac_item is None,
            }
        )
    return overlay


def validate_archive(path: Path) -> dict[str, Any]:
    contract = load_contract()
    actual_hash = sha256_file(path)
    expected_hash = contract["archive"]["sha256"]
    if actual_hash != expected_hash:
        raise VerificationError(
            f"SHA-256 distinto. Esperado {expected_hash}; obtenido {actual_hash}."
        )

    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise VerificationError("El archivo no es un ZIP válido") from exc

    with archive:
        raw_members = safe_members(archive)
        members, package_wrapper = normalize_package_layout(raw_members)
        names = sorted(members)
        ensure_no_forbidden(names)

        for root in contract["package"]["required_roots"]:
            if not any(name.startswith(root + "/") for name in names):
                raise VerificationError(f"Falta la distribución {root}/")

        for document in contract["required_root_documents"]:
            if document not in members:
                raise VerificationError(f"Falta el documento raíz {document}")

        manifest = read_member_text(
            archive, members, "MANIFIESTO_PAQUETE_V0_49_0.txt"
        )
        validation = read_member_text(archive, members, "VALIDACION_V0_49.md")
        required_manifest_tokens = (
            "V0.49.0",
            "MAC: 424 archivos físicos; 413 archivos funcionales",
            "WINDOWS: 401 archivos físicos; 390 archivos funcionales",
            "Modelos ORM: 110",
            "Rutas totales: 287",
            "Migración desde base vacía hasta 20260804_0030",
        )
        for token in required_manifest_tokens:
            if token not in manifest:
                raise VerificationError(f"El manifiesto no contiene: {token}")
        for token in (
            "ActivityFactorSelection",
            "activity_factor_selections",
            "20260804_0030",
            "115 pruebas aprobadas",
        ):
            if token not in validation and token not in manifest:
                raise VerificationError(f"La validación no contiene: {token}")

        mac = distribution_member_map(members, "MAC")
        windows = distribution_member_map(members, "WINDOWS")
        mac_report = require_distribution_structure(archive, "MAC", mac, contract)
        windows_report = require_distribution_structure(
            archive, "WINDOWS", windows, contract
        )

        expected_mac = int(contract["distributions"]["MAC"]["physical_files"])
        expected_windows = int(
            contract["distributions"]["WINDOWS"]["physical_files"]
        )
        if mac_report["physical_files"] != expected_mac:
            raise VerificationError(
                f"MAC: archivos físicos esperados {expected_mac}; encontrados {mac_report['physical_files']}"
            )
        if windows_report["physical_files"] != expected_windows:
            raise VerificationError(
                f"WINDOWS: archivos físicos esperados {expected_windows}; encontrados {windows_report['physical_files']}"
            )

        shared = compare_shared_core(archive, mac, windows)
        overlay = windows_overlay_entries(archive, mac, windows)

        return {
            "status": "verified_exact_dual_archive",
            "archive": path.name,
            "sha256": actual_hash,
            "release": contract["release"],
            "package_wrapper": package_wrapper,
            "root_files": len([name for name in names if "/" not in name]),
            "mac": mac_report,
            "windows": windows_report,
            "shared_core": shared,
            "windows_overlay_files": len(overlay),
            "windows_overlay": overlay,
            "safe_to_stage": True,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    path = args.archive.expanduser().resolve()
    if not path.is_file():
        print(f"ERROR V0.49: no existe {path}", file=sys.stderr)
        return 1
    try:
        report = validate_archive(path)
    except (VerificationError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"ERROR V0.49: {exc}", file=sys.stderr)
        return 1
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
