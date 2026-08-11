#!/usr/bin/env python3
"""Valida e instala un paquete histórico completo de Marca Maestra.

Solo acepta los cuatro PNG oficiales. Lee ZIPs sin ``extractall``, rechaza rutas
inseguras/symlinks, valida PNG por chunks y CRC y no transforma imágenes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import struct
import tempfile
import zipfile
import zlib
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[2]
DESTINATION = ROOT / "app" / "static" / "img" / "brand"
BRAND_MANIFEST = ROOT / "app" / "static" / "img" / "brand-manifest.json"
TEMPLATES = ROOT / "app" / "templates"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_MEMBER_BYTES = 25 * 1024 * 1024
MAX_TOTAL_BYTES = 150 * 1024 * 1024

ASSET_KEYS = {
    "logo-oficial.png": "logo_primary",
    "logo-oficial-blanco.png": "logo_reversed",
    "favicon-64.png": "favicon_64",
    "favicon-256.png": "favicon_256",
}
REQUIRED = tuple(ASSET_KEYS)
REFERENCE_REPLACEMENTS = {
    "img/brand-primary.svg": "img/brand/logo-oficial.png",
    "img/logo.svg": "img/brand/logo-oficial.png",
    "img/brand-reversed.svg": "img/brand/logo-oficial-blanco.png",
    "img/logo-white.svg": "img/brand/logo-oficial-blanco.png",
    "img/brand-symbol.svg": "img/brand/favicon-64.png",
    "img/favicon.svg": "img/brand/favicon-64.png",
}


class MasterPackageError(RuntimeError):
    """El paquete no puede instalarse como Marca Maestra exacta."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_png_metadata(data: bytes, filename: str) -> dict[str, int | bool]:
    if not data.startswith(PNG_SIGNATURE):
        raise MasterPackageError(f"{filename} no es un PNG válido")
    offset = len(PNG_SIGNATURE)
    width = height = bit_depth = color_type = None
    seen_ihdr = False
    seen_iend = False
    while offset < len(data):
        if offset + 12 > len(data):
            raise MasterPackageError(f"{filename} está truncado")
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = data[offset + 4 : offset + 8]
        start = offset + 8
        end = start + length
        crc_end = end + 4
        if crc_end > len(data):
            raise MasterPackageError(f"{filename} está truncado")
        payload = data[start:end]
        expected_crc = struct.unpack(">I", data[end:crc_end])[0]
        actual_crc = zlib.crc32(kind)
        actual_crc = zlib.crc32(payload, actual_crc) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise MasterPackageError(f"{filename} tiene CRC inválido")
        if not seen_ihdr:
            if kind != b"IHDR" or length != 13:
                raise MasterPackageError(f"{filename} no contiene IHDR inicial válido")
            width, height, bit_depth, color_type = struct.unpack(">IIBB", payload[:10])
            if width < 1 or height < 1:
                raise MasterPackageError(f"{filename} tiene dimensiones inválidas")
            seen_ihdr = True
        if kind == b"IEND":
            if length != 0 or crc_end != len(data):
                raise MasterPackageError(f"{filename} tiene IEND inválido o datos posteriores")
            seen_iend = True
            break
        offset = crc_end
    if not seen_ihdr or not seen_iend:
        raise MasterPackageError(f"{filename} está incompleto")
    assert None not in (width, height, bit_depth, color_type)
    return {
        "width": int(width),
        "height": int(height),
        "bit_depth": int(bit_depth),
        "color_type": int(color_type),
        "has_alpha": int(color_type) in {4, 6} or b"tRNS" in data,
    }


def _safe_zip_entries(archive: zipfile.ZipFile) -> Iterator[tuple[str, bytes]]:
    total = 0
    for item in archive.infolist():
        if item.is_dir():
            continue
        path = Path(item.filename)
        mode = (item.external_attr >> 16) & 0xFFFF
        if path.is_absolute() or ".." in path.parts:
            raise MasterPackageError(f"Ruta insegura dentro del ZIP: {item.filename}")
        if stat.S_ISLNK(mode):
            raise MasterPackageError(f"Symlink no permitido dentro del ZIP: {item.filename}")
        if item.file_size > MAX_MEMBER_BYTES:
            raise MasterPackageError(f"Miembro demasiado grande: {item.filename}")
        total += item.file_size
        if total > MAX_TOTAL_BYTES:
            raise MasterPackageError("El ZIP excede el límite total descomprimido")
        yield item.filename, archive.read(item)


def _directory_entries(root: Path) -> Iterator[tuple[str, bytes]]:
    total = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.is_symlink():
            raise MasterPackageError(f"Symlink no permitido: {path}")
        size = path.stat().st_size
        if size > MAX_MEMBER_BYTES:
            continue
        total += size
        if total > MAX_TOTAL_BYTES:
            raise MasterPackageError("La carpeta excede el límite total de lectura")
        yield path.relative_to(root).as_posix(), path.read_bytes()


def source_entries(source: Path) -> Iterator[tuple[str, bytes]]:
    if source.is_dir():
        yield from _directory_entries(source)
        return
    if source.suffix.lower() != ".zip":
        raise MasterPackageError("La fuente debe ser una carpeta o un ZIP histórico")
    try:
        archive = zipfile.ZipFile(source)
    except zipfile.BadZipFile as exc:
        raise MasterPackageError("El archivo no es un ZIP válido") from exc
    with archive:
        yield from _safe_zip_entries(archive)


def load_exact_assets(source: Path) -> dict[str, bytes]:
    matches: dict[str, list[tuple[str, bytes]]] = {name: [] for name in REQUIRED}
    for member, data in source_entries(source):
        name = Path(member).name
        if name in matches:
            matches[name].append((member, data))
    resolved: dict[str, bytes] = {}
    for name, candidates in matches.items():
        if not candidates:
            raise MasterPackageError(f"Falta el activo oficial requerido: {name}")
        hashes = {digest(data) for _, data in candidates}
        if len(hashes) != 1:
            listed = ", ".join(member for member, _ in candidates)
            raise MasterPackageError(f"Existen copias distintas de {name}: {listed}")
        resolved[name] = candidates[0][1]
    return resolved


def build_inventory(assets: dict[str, bytes]) -> dict[str, dict[str, Any]]:
    inventory: dict[str, dict[str, Any]] = {}
    for filename, data in assets.items():
        inventory[filename] = {"sha256": digest(data), "bytes": len(data), **read_png_metadata(data, filename)}
    if (inventory["logo-oficial.png"]["width"], inventory["logo-oficial.png"]["height"]) != (470, 195):
        raise MasterPackageError("logo-oficial.png debe medir exactamente 470 × 195 px")
    if (inventory["favicon-64.png"]["width"], inventory["favicon-64.png"]["height"]) != (64, 64):
        raise MasterPackageError("favicon-64.png debe medir exactamente 64 × 64 px")
    if (inventory["favicon-256.png"]["width"], inventory["favicon-256.png"]["height"]) != (256, 256):
        raise MasterPackageError("favicon-256.png debe medir exactamente 256 × 256 px")
    return inventory


def manifest_assets(inventory: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        key: {"path": f"app/static/img/brand/{filename}", **inventory[filename]}
        for filename, key in ASSET_KEYS.items()
    }


def template_paths() -> list[Path]:
    return sorted(TEMPLATES.rglob("*.html"))


def plan_template_updates() -> dict[Path, str]:
    paths = template_paths()
    planned: dict[Path, str] = {}
    for path in paths:
        original = path.read_text(encoding="utf-8")
        updated = original
        for legacy, official in REFERENCE_REPLACEMENTS.items():
            updated = updated.replace(legacy, official)
        if updated != original:
            planned[path] = updated
    combined = "\n".join(planned.get(path, path.read_text(encoding="utf-8")) for path in paths)
    for legacy in REFERENCE_REPLACEMENTS:
        if legacy in combined:
            raise MasterPackageError(f"No pudo retirarse la referencia legacy: {legacy}")
    for official in ("logo-oficial.png", "logo-oficial-blanco.png", "favicon-64.png"):
        if official not in combined:
            raise MasterPackageError(f"La activación no referencia el activo oficial: {official}")
    return planned


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
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


def activate(source: Path, assets: dict[str, bytes], inventory: dict[str, dict[str, Any]], updates: dict[Path, str]) -> None:
    manifest = json.loads(BRAND_MANIFEST.read_text(encoding="utf-8"))
    manifest["approved_master"] = {
        "status": "installed_exact_master",
        "source": source.name,
        "geometry": "C circular envolvente, barras ascendentes y hoja integrada",
        "redraw_allowed": False,
        "placeholder_allowed": False,
        "assets": manifest_assets(inventory),
    }
    for filename, data in assets.items():
        atomic_write_bytes(DESTINATION / filename, data)
    for path, content in updates.items():
        atomic_write_text(path, content)
    atomic_write_text(BRAND_MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="ZIP o carpeta de Marca Maestra v1")
    parser.add_argument("--apply", action="store_true", help="Instalar y activar solo un paquete completo validado")
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    if not source.exists():
        print(f"ERROR DE MARCA: no existe la fuente: {source}")
        return 1
    try:
        assets = load_exact_assets(source)
        inventory = build_inventory(assets)
        updates = plan_template_updates()
        report = {
            "source": source.name,
            "assets": manifest_assets(inventory),
            "templates_to_update": [str(path.relative_to(ROOT)) for path in updates],
            "transformation": "none",
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if not args.apply:
            print("Validación completada. Usa --apply solo para instalar el paquete completo exacto.")
            return 0
        activate(source, assets, inventory, updates)
        print(f"Marca Maestra instalada y activada en {DESTINATION}")
        return 0
    except (MasterPackageError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"ERROR DE MARCA: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
