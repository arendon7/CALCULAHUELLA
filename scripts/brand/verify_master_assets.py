#!/usr/bin/env python3
"""Verifica la identidad canónica aprobada desde V1.4.2.

La validación es byte-a-byte: no reconstruye, convierte, recolorea ni deriva
variantes del logo. Los únicos activos autorizados son el logo clásico principal
y su símbolo/favIcon con las huellas SHA-256 históricas aprobadas.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "app" / "static" / "img" / "brand-manifest.json"
TEMPLATES = ROOT / "app" / "templates"
APPROVED_DESCRIPTOR = "Plataforma digital de gestión de huella de carbono"
APPROVED_CLAIM = "Convierte tus datos en decisiones climáticas"
INSTALLED_STATUS = "installed_exact_classic"
EXPECTED_ASSETS = {
    "logo_primary": {
        "path": "app/static/img/brand-primary.svg",
        "authorized_source_path": "assets_marca_canonica/logo_clasico_primary.svg",
        "sha256": "04a9b2557c1aff819eef52364dbe88677044299a6c868a7318703fdccffa638e",
        "bytes": 1484,
    },
    "symbol": {
        "path": "app/static/img/brand-symbol.svg",
        "authorized_source_path": "assets_marca_canonica/logo_clasico_symbol.svg",
        "sha256": "c43e33c89860aac5d7f582009b7d53e7902aa7704c9484fefcb1e2a2f99ce3e8",
        "bytes": 855,
    },
}
FORBIDDEN_ACTIVE_ASSETS = (
    "brand-reversed.svg",
    "logo.svg",
    "logo-white.svg",
    "favicon.svg",
    "logo-oficial.png",
    "logo-oficial-blanco.png",
    "favicon-64.png",
    "favicon-256.png",
)


class BrandValidationError(RuntimeError):
    """La identidad activa no coincide con el canon aprobado."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest() -> dict[str, Any]:
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BrandValidationError("Falta app/static/img/brand-manifest.json") from exc
    except json.JSONDecodeError as exc:
        raise BrandValidationError(f"Manifest JSON inválido: {exc}") from exc
    if not isinstance(data, dict):
        raise BrandValidationError("El manifest debe ser un objeto JSON")
    return data


def validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    if manifest.get("brand") != "Calcula tu Huella":
        raise BrandValidationError("Nombre de marca inconsistente")
    if manifest.get("descriptor") != APPROVED_DESCRIPTOR:
        raise BrandValidationError("Descriptor distinto del aprobado")
    if manifest.get("claim") != APPROVED_CLAIM:
        raise BrandValidationError("Claim distinto del aprobado")

    approved = manifest.get("approved_master")
    if not isinstance(approved, dict):
        raise BrandValidationError("Falta approved_master")
    if approved.get("status") != INSTALLED_STATUS:
        raise BrandValidationError(f"Estado canónico inválido: {approved.get('status')!r}")
    if approved.get("decision_version") != "1.4.2":
        raise BrandValidationError("La decisión de marca debe estar anclada en V1.4.2")
    if approved.get("redraw_allowed") is not False:
        raise BrandValidationError("El contrato debe prohibir redibujos")
    if approved.get("placeholder_allowed") is not False:
        raise BrandValidationError("El contrato debe prohibir placeholders")
    if approved.get("variants_allowed") is not False:
        raise BrandValidationError("El contrato debe prohibir variantes no documentadas")

    assets = approved.get("assets")
    if not isinstance(assets, dict) or set(assets) != set(EXPECTED_ASSETS):
        raise BrandValidationError("Solo se autorizan logo_primary y symbol")
    for key, expected in EXPECTED_ASSETS.items():
        item = assets.get(key)
        if not isinstance(item, dict):
            raise BrandValidationError(f"Falta definición de {key}")
        for field, value in expected.items():
            if item.get(field) != value:
                raise BrandValidationError(
                    f"{key}.{field} esperado {value!r}, obtenido {item.get(field)!r}"
                )
    return approved


def validate_exact_files() -> None:
    for key, expected in EXPECTED_ASSETS.items():
        path = ROOT / str(expected["path"])
        if not path.is_file():
            raise BrandValidationError(f"No existe {expected['path']}")
        actual_size = path.stat().st_size
        actual_hash = sha256(path)
        if actual_size != expected["bytes"]:
            raise BrandValidationError(
                f"{key}: bytes esperados {expected['bytes']}, obtenidos {actual_size}"
            )
        if actual_hash != expected["sha256"]:
            raise BrandValidationError(
                f"{key}: SHA-256 esperado {expected['sha256']}, obtenido {actual_hash}"
            )


def template_text() -> dict[Path, str]:
    return {
        path: path.read_text(encoding="utf-8")
        for path in sorted(TEMPLATES.rglob("*.html"))
    }


def validate_active_surfaces() -> None:
    templates = template_text()
    combined = "\n".join(templates.values())
    for forbidden in FORBIDDEN_ACTIVE_ASSETS:
        if forbidden in combined:
            raise BrandValidationError(f"Referencia de marca no canónica activa: {forbidden}")

    base = templates.get(TEMPLATES / "base.html", "")
    public_base = templates.get(TEMPLATES / "public_base.html", "")
    if "img/brand-primary.svg" not in base or "img/brand-symbol.svg" not in base:
        raise BrandValidationError("El shell autenticado no usa ambos activos canónicos")
    if public_base.count("img/brand-primary.svg") < 2:
        raise BrandValidationError("Encabezado y pie públicos deben usar el logo principal exacto")
    if "img/brand-symbol.svg" not in public_base:
        raise BrandValidationError("El favicon público debe usar el símbolo exacto")


def validate() -> None:
    validate_manifest(load_manifest())
    validate_exact_files()
    validate_active_surfaces()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-canonical",
        action="store_true",
        help="Alias explícito: la validación ya es estricta por defecto.",
    )
    parser.add_argument(
        "--require-master",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.parse_args()
    try:
        validate()
        print("Marca canónica V1.4.2: VALIDADA · 2/2 activos exactos")
        return 0
    except (BrandValidationError, OSError, UnicodeError) as exc:
        print(f"ERROR DE MARCA: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
