#!/usr/bin/env python3
"""Valida el contrato de verdad de Marca Maestra.

En estado recuperable permite que los PNG exactos sigan pendientes, pero impide
que activos legacy se declaren como canónicos. Con ``--require-master`` exige
los cuatro PNG exactos y sus metadatos verificables.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "app" / "static" / "img" / "brand-manifest.json"
APPROVED_DESCRIPTOR = "Plataforma digital de gestión de huella de carbono"
APPROVED_CLAIM = "Convierte tus datos en decisiones climáticas"
RECOVERABLE_STATUS = "recoverable_exact_primary_from_embedded_html"
INSTALLED_STATUS = "installed_exact_master"
PENDING_INDEPENDENT_ASSETS = {
    "logo-oficial-blanco.png",
    "favicon-64.png",
    "favicon-256.png",
}


class BrandValidationError(RuntimeError):
    """Error de consistencia de Marca Maestra."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as source:
        header = source.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise BrandValidationError(f"No es un PNG válido: {path.relative_to(ROOT)}")
    return struct.unpack(">II", header[16:24])


def load_manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.exists():
        raise BrandValidationError("Falta app/static/img/brand-manifest.json")
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BrandValidationError(f"Manifest JSON inválido: {exc}") from exc
    if not isinstance(data, dict):
        raise BrandValidationError("El manifest debe ser un objeto JSON")
    return data


def validate_recoverable_state(approved: dict[str, Any]) -> None:
    expected = approved.get("expected_primary")
    if not isinstance(expected, dict):
        raise BrandValidationError("Falta approved_master.expected_primary")
    required_expected = {
        "filename": "logo-oficial.png",
        "width": 470,
        "height": 195,
        "encoding": "PNG data URI base64",
        "minimum_independent_sources": 2,
        "transformation": "none",
    }
    for field, value in required_expected.items():
        if expected.get(field) != value:
            raise BrandValidationError(
                f"expected_primary.{field} debe ser {value!r}, no {expected.get(field)!r}"
            )

    sources = approved.get("verified_source_names")
    if not isinstance(sources, list) or len(set(map(str, sources))) < 2:
        raise BrandValidationError("Se requieren al menos dos fuentes históricas independientes")

    pending = approved.get("pending_independent_assets")
    if not isinstance(pending, list) or set(map(str, pending)) != PENDING_INDEPENDENT_ASSETS:
        raise BrandValidationError("La lista de activos independientes pendientes es inconsistente")


def validate_contract(manifest: dict[str, Any]) -> None:
    if manifest.get("brand") != "Calcula tu Huella":
        raise BrandValidationError("Nombre de marca inconsistente")
    if manifest.get("descriptor") != APPROVED_DESCRIPTOR:
        raise BrandValidationError("Descriptor distinto del aprobado")
    if manifest.get("claim") != APPROVED_CLAIM:
        raise BrandValidationError("Claim distinto del aprobado")
    if "canonical_assets" in manifest:
        raise BrandValidationError("No se permiten activos legacy falsamente declarados como canónicos")

    approved = manifest.get("approved_master")
    if not isinstance(approved, dict):
        raise BrandValidationError("Falta approved_master")
    if approved.get("redraw_allowed") is not False:
        raise BrandValidationError("El contrato debe prohibir redibujos")
    if approved.get("placeholder_allowed") is not False:
        raise BrandValidationError("El contrato debe prohibir placeholders")

    status = approved.get("status")
    if status == RECOVERABLE_STATUS:
        validate_recoverable_state(approved)
    elif status != INSTALLED_STATUS:
        raise BrandValidationError(f"Estado de Marca Maestra no reconocido: {status!r}")


def validate_installed_assets(manifest: dict[str, Any]) -> None:
    approved = manifest["approved_master"]
    if approved.get("status") != INSTALLED_STATUS:
        raise BrandValidationError(
            f"La Marca Maestra exacta aún no está instalada. Estado esperado: {INSTALLED_STATUS}"
        )

    assets = approved.get("assets")
    if not isinstance(assets, dict) or not assets:
        raise BrandValidationError("Falta el inventario approved_master.assets")

    required = {
        "logo_primary": "app/static/img/brand/logo-oficial.png",
        "logo_reversed": "app/static/img/brand/logo-oficial-blanco.png",
        "favicon_64": "app/static/img/brand/favicon-64.png",
        "favicon_256": "app/static/img/brand/favicon-256.png",
    }
    for key, default_path in required.items():
        item = assets.get(key)
        if not isinstance(item, dict):
            raise BrandValidationError(f"Falta definición del activo {key}")
        relative = str(item.get("path", default_path))
        path = ROOT / relative
        if not path.is_file():
            raise BrandValidationError(f"No existe {relative}")
        actual_width, actual_height = png_dimensions(path)
        actual = {
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "width": actual_width,
            "height": actual_height,
        }
        for field, value in actual.items():
            if item.get(field) != value:
                raise BrandValidationError(
                    f"{key}: {field} esperado {item.get(field)!r}, obtenido {value!r}"
                )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-master",
        action="store_true",
        help="Exige que los cuatro activos maestros exactos estén instalados.",
    )
    args = parser.parse_args()

    try:
        manifest = load_manifest()
        validate_contract(manifest)
        status = manifest["approved_master"].get("status")
        if args.require_master:
            validate_installed_assets(manifest)
            print("Marca Maestra exacta: VALIDADA")
        else:
            print(f"Contrato de marca: VALIDADO · estado del maestro: {status}")
        return 0
    except BrandValidationError as exc:
        print(f"ERROR DE MARCA: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
