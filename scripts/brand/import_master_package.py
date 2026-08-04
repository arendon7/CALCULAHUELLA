#!/usr/bin/env python3
"""Valida, instala y activa el paquete histórico exacto de Marca Maestra v1.

No genera, recolorea, redibuja ni deriva activos. Solo acepta los cuatro PNG
oficiales, registra sus metadatos y sustituye referencias legacy cuando el
paquete completo ha superado todas las validaciones.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import tempfile
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DESTINATION = ROOT / "app" / "static" / "img" / "brand"
BRAND_MANIFEST = ROOT / "app" / "static" / "img" / "brand-manifest.json"
TEMPLATES = ROOT / "app" / "templates"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_END = b"IEND\xaeB`\x82"

ASSET_KEYS = {
    "logo-oficial.png": "logo_primary",
    "logo-oficial-blanco.png": "logo_reversed",
    "favicon-64.png": "favicon_64",
    "favicon-256.png": "favicon_256",
}
REQUIRED = tuple(ASSET_KEYS)
REFERENCE_REPLACEMENTS = {
    "img/brand-primary.svg": "img/brand/logo-oficial.png",
    "img/brand-reversed.svg": "img/brand/logo-oficial-blanco.png",
    "img/brand-symbol.svg": "img/brand/favicon-64.png",
}


class MasterPackageError(RuntimeError):
    """El paquete no puede instalarse como Marca Maestra exacta."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_png_metadata(path: Path) -> dict[str, int | bool]:
    data = path.read_bytes()
    if len(data) < 33 or not data.startswith(PNG_SIGNATURE):
        raise MasterPackageError(f"{path.name} no es un PNG válido")
    if data[12:16] != b"IHDR":
        raise MasterPackageError(f"{path.name} no contiene IHDR válido")
    if not data.endswith(PNG_END):
        raise MasterPackageError(f"{path.name} está truncado: falta IEND")
    width, height, bit_depth, color_type = struct.unpack(">IIBB", data[16:26])
    if width < 1 or height < 1:
        raise MasterPackageError(f"{path.name} tiene dimensiones inválidas")
    return {
        "width": width,
        "height": height,
        "bit_depth": bit_depth,
        "color_type": color_type,
        "has_alpha": color_type in {4, 6} or b"tRNS" in data,
    }


def locate_assets(root: Path) -> dict[str, Path]:
    matches: dict[str, list[Path]] = {name: [] for name in REQUIRED}
    for path in root.rglob("*"):
        if path.is_file() and path.name in matches:
            matches[path.name].append(path)

    resolved: dict[str, Path] = {}
    for name, candidates in matches.items():
        if not candidates:
            raise MasterPackageError(f"Falta el activo oficial requerido: {name}")
        hashes = {sha256(path) for path in candidates}
        if len(hashes) > 1:
            listed = "\n  - ".join(str(path) for path in candidates)
            raise MasterPackageError(f"Existen copias distintas de {name}:\n  - {listed}")
        resolved[name] = candidates[0]
    return resolved


def extract_source(source: Path, temporary: Path) -> Path:
    if source.is_dir():
        return source
    if source.suffix.lower() != ".zip":
        raise MasterPackageError("La fuente debe ser una carpeta o un ZIP histórico")
    try:
        archive = zipfile.ZipFile(source)
    except zipfile.BadZipFile as exc:
        raise MasterPackageError("El archivo no es un ZIP válido") from exc
    with archive:
        root = temporary.resolve()
        for member in archive.infolist():
            destination = (temporary / member.filename).resolve()
            if root not in destination.parents and destination != root:
                raise MasterPackageError(f"Ruta insegura dentro del ZIP: {member.filename}")
        archive.extractall(temporary)
    return temporary


def build_inventory(assets: dict[str, Path]) -> dict[str, dict[str, Any]]:
    inventory: dict[str, dict[str, Any]] = {}
    for filename, path in assets.items():
        inventory[filename] = {
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
            **read_png_metadata(path),
        }

    if (inventory["logo-oficial.png"]["width"], inventory["logo-oficial.png"]["height"]) != (470, 195):
        raise MasterPackageError("logo-oficial.png debe conservar el lienzo aprobado de 470 × 195 px")
    if (inventory["favicon-64.png"]["width"], inventory["favicon-64.png"]["height"]) != (64, 64):
        raise MasterPackageError("favicon-64.png debe medir exactamente 64 × 64 px")
    if (inventory["favicon-256.png"]["width"], inventory["favicon-256.png"]["height"]) != (256, 256):
        raise MasterPackageError("favicon-256.png debe medir exactamente 256 × 256 px")
    return inventory


def manifest_assets(inventory: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for filename, key in ASSET_KEYS.items():
        result[key] = {
            "path": f"app/static/img/brand/{filename}",
            **inventory[filename],
        }
    return result


def plan_template_updates() -> dict[Path, str]:
    planned: dict[Path, str] = {}
    for path in sorted(TEMPLATES.glob("*.html")):
        original = path.read_text(encoding="utf-8")
        updated = original
        for legacy, official in REFERENCE_REPLACEMENTS.items():
            updated = updated.replace(legacy, official)
        if updated != original:
            planned[path] = updated

    combined = "\n".join(
        planned.get(path, path.read_text(encoding="utf-8"))
        for path in sorted(TEMPLATES.glob("*.html"))
    )
    for legacy in REFERENCE_REPLACEMENTS:
        if legacy in combined:
            raise MasterPackageError(f"No pudo retirarse la referencia legacy: {legacy}")
    for official in ("logo-oficial.png", "logo-oficial-blanco.png", "favicon-64.png"):
        if official not in combined:
            raise MasterPackageError(f"La activación no referencia el activo oficial: {official}")
    return planned


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as target:
            target.write(data)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_write_text(path: Path, content: str) -> None:
    atomic_write_bytes(path, content.encode("utf-8"))


def activate(
    source: Path,
    assets: dict[str, Path],
    inventory: dict[str, dict[str, Any]],
    template_updates: dict[Path, str],
) -> None:
    manifest = json.loads(BRAND_MANIFEST.read_text(encoding="utf-8"))
    manifest["approved_master"] = {
        "status": "installed_exact_master",
        "source": source.name,
        "geometry": "C circular envolvente, barras ascendentes y hoja integrada",
        "redraw_allowed": False,
        "placeholder_allowed": False,
        "assets": manifest_assets(inventory),
    }

    # Primero se materializan los cuatro binarios; el manifiesto se escribe al final
    # para que una interrupción no declare instalada una migración incompleta.
    for filename, path in assets.items():
        atomic_write_bytes(DESTINATION / filename, path.read_bytes())
    for path, content in template_updates.items():
        atomic_write_text(path, content)
    atomic_write_text(BRAND_MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="ZIP o carpeta de Marca Maestra v1")
    parser.add_argument("--apply", action="store_true", help="Instalar y activar los archivos exactos")
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    if not source.exists():
        print(f"ERROR DE MARCA: no existe la fuente: {source}")
        return 1

    try:
        with tempfile.TemporaryDirectory(prefix="cth-brand-") as temp_dir:
            extracted = extract_source(source, Path(temp_dir))
            assets = locate_assets(extracted)
            inventory = build_inventory(assets)
            template_updates = plan_template_updates()

            report = {
                "source": source.name,
                "assets": manifest_assets(inventory),
                "templates_to_update": [str(path.relative_to(ROOT)) for path in template_updates],
                "transformation": "none",
            }
            print(json.dumps(report, ensure_ascii=False, indent=2))
            if not args.apply:
                print("Validación completada. Usa --apply para instalar y activar la Marca Maestra.")
                return 0

            activate(source, assets, inventory, template_updates)
            print(f"Marca Maestra instalada y activada en {DESTINATION}")
            print("Ejecuta: make brand-require-master")
            return 0
    except (MasterPackageError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"ERROR DE MARCA: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
