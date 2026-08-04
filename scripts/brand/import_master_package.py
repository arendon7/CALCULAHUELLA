#!/usr/bin/env python3
"""Importa el paquete histórico exacto de Marca Maestra v1.

No genera, recolorea, redibuja ni deriva activos. Solo acepta los cuatro PNG
oficiales, valida su estructura y registra hashes/dimensiones antes de copiarlos.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESTINATION = ROOT / "app" / "static" / "img" / "brand"
BRAND_MANIFEST = ROOT / "app" / "static" / "img" / "brand-manifest.json"
REQUIRED = ("logo-oficial.png", "logo-oficial-blanco.png", "favicon-64.png", "favicon-256.png")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_png_metadata(path: Path) -> dict[str, int | bool]:
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError(f"{path.name} no es un PNG válido")
    if len(data) < 33 or data[12:16] != b"IHDR":
        raise ValueError(f"{path.name} no contiene IHDR válido")
    width, height, bit_depth, color_type = struct.unpack(">IIBB", data[16:26])
    has_alpha = color_type in {4, 6} or b"tRNS" in data
    if width < 1 or height < 1:
        raise ValueError(f"{path.name} tiene dimensiones inválidas")
    return {"width": width, "height": height, "bit_depth": bit_depth, "color_type": color_type, "has_alpha": has_alpha}


def locate_assets(root: Path) -> dict[str, Path]:
    matches: dict[str, list[Path]] = {name: [] for name in REQUIRED}
    for path in root.rglob("*"):
        if path.is_file() and path.name in matches:
            matches[path.name].append(path)
    resolved: dict[str, Path] = {}
    for name, candidates in matches.items():
        if not candidates:
            raise FileNotFoundError(f"Falta el activo oficial requerido: {name}")
        hashes = {sha256(path) for path in candidates}
        if len(hashes) > 1:
            listed = "\n  - ".join(str(path) for path in candidates)
            raise ValueError(f"Existen copias distintas de {name}:\n  - {listed}")
        resolved[name] = candidates[0]
    return resolved


def extract_source(source: Path, temporary: Path) -> Path:
    if source.is_dir():
        return source
    if source.suffix.lower() != ".zip":
        raise ValueError("La fuente debe ser una carpeta o un ZIP histórico")
    with zipfile.ZipFile(source) as archive:
        for member in archive.infolist():
            destination = (temporary / member.filename).resolve()
            if temporary.resolve() not in destination.parents and destination != temporary.resolve():
                raise ValueError(f"Ruta insegura dentro del ZIP: {member.filename}")
        archive.extractall(temporary)
    return temporary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="ZIP o carpeta de Marca Maestra v1")
    parser.add_argument("--apply", action="store_true", help="Copiar activos y actualizar el manifiesto")
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    if not source.exists():
        raise SystemExit(f"No existe la fuente: {source}")

    with tempfile.TemporaryDirectory(prefix="cth-brand-") as temp_dir:
        extracted = extract_source(source, Path(temp_dir))
        assets = locate_assets(extracted)
        inventory: dict[str, dict[str, int | str | bool]] = {}
        for name, path in assets.items():
            inventory[name] = {"sha256": sha256(path), "bytes": path.stat().st_size, **read_png_metadata(path)}

        if (inventory["favicon-64.png"]["width"], inventory["favicon-64.png"]["height"]) != (64, 64):
            raise ValueError("favicon-64.png debe medir exactamente 64 × 64 px")
        if (inventory["favicon-256.png"]["width"], inventory["favicon-256.png"]["height"]) != (256, 256):
            raise ValueError("favicon-256.png debe medir exactamente 256 × 256 px")
        for name in ("logo-oficial.png", "logo-oficial-blanco.png"):
            if not inventory[name]["has_alpha"]:
                raise ValueError(f"{name} debe conservar transparencia")

        print(json.dumps(inventory, ensure_ascii=False, indent=2))
        if not args.apply:
            print("Validación completada. Usa --apply para instalar los archivos exactos.")
            return

        DESTINATION.mkdir(parents=True, exist_ok=True)
        for name, path in assets.items():
            shutil.copy2(path, DESTINATION / name)
        manifest = json.loads(BRAND_MANIFEST.read_text(encoding="utf-8"))
        manifest["approved_master"] = {
            "status": "installed_exact_historical_binary",
            "source": source.name,
            "geometry": "C circular envolvente, barras ascendentes y hoja integrada",
            "redraw_allowed": False,
            "placeholder_allowed": False,
            "assets": inventory,
        }
        manifest.pop("compatibility_assets", None)
        BRAND_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Marca Maestra instalada en {DESTINATION}")


if __name__ == "__main__":
    main()
