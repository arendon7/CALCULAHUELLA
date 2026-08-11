#!/usr/bin/env python3
"""Valida el contrato de verdad y, opcionalmente, la Marca Maestra instalada."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "app" / "static" / "img" / "brand-manifest.json"
TEMPLATES = ROOT / "app" / "templates"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
APPROVED_DESCRIPTOR = "Plataforma digital de gestión de huella de carbono"
APPROVED_CLAIM = "Convierte tus datos en decisiones climáticas"
RECOVERABLE_STATUS = "recoverable_exact_primary_from_embedded_html"
INSTALLED_STATUS = "installed_exact_master"
PENDING_INDEPENDENT_ASSETS = {"logo-oficial-blanco.png", "favicon-64.png", "favicon-256.png"}
LEGACY_REFERENCES = {
    "img/brand-primary.svg",
    "img/logo.svg",
    "img/brand-reversed.svg",
    "img/logo-white.svg",
    "img/brand-symbol.svg",
    "img/favicon.svg",
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
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise BrandValidationError(f"No es un PNG válido: {path.relative_to(ROOT)}")
    offset = len(PNG_SIGNATURE)
    width = height = None
    first = True
    complete = False
    while offset < len(data):
        if offset + 12 > len(data):
            raise BrandValidationError(f"PNG truncado: {path.relative_to(ROOT)}")
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = data[offset + 4 : offset + 8]
        start = offset + 8
        end = start + length
        crc_end = end + 4
        if crc_end > len(data):
            raise BrandValidationError(f"PNG truncado: {path.relative_to(ROOT)}")
        payload = data[start:end]
        expected_crc = struct.unpack(">I", data[end:crc_end])[0]
        actual_crc = zlib.crc32(kind)
        actual_crc = zlib.crc32(payload, actual_crc) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise BrandValidationError(f"PNG con CRC inválido: {path.relative_to(ROOT)}")
        if first:
            if kind != b"IHDR" or length != 13:
                raise BrandValidationError(f"PNG sin IHDR inicial válido: {path.relative_to(ROOT)}")
            width, height = struct.unpack(">II", payload[:8])
            if width < 1 or height < 1:
                raise BrandValidationError(f"PNG con dimensiones inválidas: {path.relative_to(ROOT)}")
            first = False
        if kind == b"IEND":
            if length != 0 or crc_end != len(data):
                raise BrandValidationError(f"PNG con IEND inválido: {path.relative_to(ROOT)}")
            complete = True
            break
        offset = crc_end
    if not complete or width is None or height is None:
        raise BrandValidationError(f"PNG incompleto: {path.relative_to(ROOT)}")
    return width, height


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
    required = {
        "filename": "logo-oficial.png",
        "width": 470,
        "height": 195,
        "encoding": "PNG data URI base64",
        "minimum_independent_sources": 2,
        "transformation": "none",
    }
    if not isinstance(expected, dict):
        raise BrandValidationError("Falta approved_master.expected_primary")
    for field, value in required.items():
        if expected.get(field) != value:
            raise BrandValidationError(f"expected_primary.{field} debe ser {value!r}")
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
    if approved.get("redraw_allowed") is not False or approved.get("placeholder_allowed") is not False:
        raise BrandValidationError("El contrato debe prohibir redibujos y placeholders")
    status = approved.get("status")
    if status == RECOVERABLE_STATUS:
        validate_recoverable_state(approved)
    elif status != INSTALLED_STATUS:
        raise BrandValidationError(f"Estado de Marca Maestra no reconocido: {status!r}")


def validate_template_activation() -> None:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in sorted(TEMPLATES.rglob("*.html")))
    for legacy in LEGACY_REFERENCES:
        if legacy in combined:
            raise BrandValidationError(f"Referencia legacy activa: {legacy}")
    for official in ("logo-oficial.png", "logo-oficial-blanco.png", "favicon-64.png"):
        if official not in combined:
            raise BrandValidationError(f"El activo oficial no está referenciado: {official}")


def validate_installed_assets(manifest: dict[str, Any]) -> None:
    approved = manifest["approved_master"]
    if approved.get("status") != INSTALLED_STATUS:
        raise BrandValidationError(f"La Marca Maestra exacta aún no está instalada. Estado esperado: {INSTALLED_STATUS}")
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
        width, height = png_dimensions(path)
        actual = {"bytes": path.stat().st_size, "sha256": sha256(path), "width": width, "height": height}
        for field, value in actual.items():
            if item.get(field) != value:
                raise BrandValidationError(f"{key}: {field} esperado {item.get(field)!r}, obtenido {value!r}")
    validate_template_activation()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-master", action="store_true", help="Exige los cuatro PNG exactos y su activación completa.")
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
