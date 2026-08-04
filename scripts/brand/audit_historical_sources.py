#!/usr/bin/env python3
"""Audita paquetes históricos de marca sin instalar ni transformar activos.

Clasifica cuatro clases de evidencia:

- paquete maestro exacto: contiene los cuatro PNG oficiales;
- HTML recuperable: conserva el PNG principal completo como data URI;
- compatibilidad legacy: SVG anteriores de huella/gráfica;
- referencia visual: tableros o imágenes útiles para UX, nunca para extraer el logo.

El comando es de solo lectura. No copia, convierte, recorta ni reescribe archivos.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import struct
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Iterator

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_END = b"IEND\xaeB`\x82"
OFFICIAL = {
    "logo-oficial.png",
    "logo-oficial-blanco.png",
    "favicon-64.png",
    "favicon-256.png",
}
LEGACY_NAMES = {
    "brand-primary.svg",
    "brand-reversed.svg",
    "brand-symbol.svg",
    "logo.svg",
    "logo-white.svg",
    "favicon.svg",
}
ARCHIVAL_VISUAL_NAMES = {
    "01_identidad_visual.png",
    "02_landing_dashboard.png",
    "03_inventario.png",
    "04_calculo_reportes.png",
    "board_maestro_identidad_calcula_tu_huella_v1.png",
}
KNOWN_PACKAGE_NAMES = {
    "calcula_tu_huella_marca_maestra_v1.zip",
    "calcula_tu_huella_front_consolidado_v0_37.zip",
}
DATA_URI = re.compile(
    rb"data:image/png;base64,(?P<payload>[A-Za-z0-9+/=\r\n\t ]+)", re.I
)
MAX_MEMBER_BYTES = 25 * 1024 * 1024


class AuditError(RuntimeError):
    """La fuente no puede auditarse de forma segura."""


@dataclass(frozen=True)
class Finding:
    source: str
    member: str
    classification: str
    filename: str
    sha256: str | None = None
    bytes: int | None = None
    width: int | None = None
    height: int | None = None
    note: str | None = None


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def png_metadata(data: bytes) -> tuple[int, int]:
    if len(data) < 33 or not data.startswith(PNG_SIGNATURE) or data[12:16] != b"IHDR":
        raise AuditError("contenido PNG inválido")
    if not data.endswith(PNG_END):
        raise AuditError("PNG truncado: falta IEND")
    return struct.unpack(">II", data[16:24])


def classify_named_file(source: str, member: str, data: bytes) -> list[Finding]:
    name = Path(member).name
    findings: list[Finding] = []
    if name in OFFICIAL:
        width, height = png_metadata(data)
        findings.append(
            Finding(
                source=source,
                member=member,
                classification="official_exact_asset",
                filename=name,
                sha256=digest(data),
                bytes=len(data),
                width=width,
                height=height,
                note="activo exacto por nombre; requiere cotejo conjunto del paquete",
            )
        )
    elif name in LEGACY_NAMES:
        note = "compatibilidad legacy; prohibido promover a Marca Maestra"
        if b"Plataforma profesional de huella de carbono" in data:
            note += "; contiene descriptor anterior"
        findings.append(
            Finding(
                source=source,
                member=member,
                classification="legacy_brand_asset",
                filename=name,
                sha256=digest(data),
                bytes=len(data),
                note=note,
            )
        )
    elif name in ARCHIVAL_VISUAL_NAMES:
        width = height = None
        try:
            width, height = png_metadata(data)
        except AuditError:
            pass
        findings.append(
            Finding(
                source=source,
                member=member,
                classification="archival_visual_reference",
                filename=name,
                sha256=digest(data),
                bytes=len(data),
                width=width,
                height=height,
                note="puede orientar UX; no autoriza recorte ni extracción de logo",
            )
        )
    return findings


def embedded_png_findings(source: str, member: str, data: bytes) -> list[Finding]:
    if not member.lower().endswith((".html", ".htm")):
        return []
    findings: list[Finding] = []
    for occurrence, match in enumerate(DATA_URI.finditer(data), start=1):
        payload = re.sub(rb"\s+", b"", match.group("payload"))
        try:
            decoded = base64.b64decode(payload, validate=True)
            width, height = png_metadata(decoded)
        except (ValueError, AuditError):
            findings.append(
                Finding(
                    source=source,
                    member=member,
                    classification="invalid_embedded_png",
                    filename=f"embedded-png-{occurrence}",
                    note="data URI inválido o truncado",
                )
            )
            continue
        classification = (
            "recoverable_primary_logo"
            if (width, height) == (470, 195)
            else "embedded_png_reference"
        )
        findings.append(
            Finding(
                source=source,
                member=member,
                classification=classification,
                filename=f"embedded-png-{occurrence}",
                sha256=digest(decoded),
                bytes=len(decoded),
                width=width,
                height=height,
                note="sin transformación",
            )
        )
    return findings


def inspect_bytes(source: str, member: str, data: bytes) -> list[Finding]:
    return classify_named_file(source, member, data) + embedded_png_findings(source, member, data)


def iter_directory(root: Path) -> Iterator[tuple[str, bytes]]:
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.stat().st_size > MAX_MEMBER_BYTES:
            continue
        yield path.relative_to(root).as_posix(), path.read_bytes()


def safe_zip_members(archive: zipfile.ZipFile) -> Iterator[tuple[str, bytes]]:
    for item in archive.infolist():
        if item.is_dir() or item.file_size > MAX_MEMBER_BYTES:
            continue
        normalized = Path(item.filename)
        if normalized.is_absolute() or ".." in normalized.parts:
            raise AuditError(f"ruta insegura dentro del ZIP: {item.filename}")
        yield item.filename, archive.read(item)


def audit_source(path: Path) -> list[Finding]:
    source = str(path)
    findings: list[Finding] = []
    if path.is_dir():
        iterator: Iterable[tuple[str, bytes]] = iter_directory(path)
    elif path.suffix.lower() == ".zip":
        try:
            archive = zipfile.ZipFile(path)
        except zipfile.BadZipFile as exc:
            raise AuditError(f"ZIP inválido: {path}") from exc
        with archive:
            for member, data in safe_zip_members(archive):
                findings.extend(inspect_bytes(source, member, data))
        return findings
    elif path.is_file():
        iterator = [(path.name, path.read_bytes())]
    else:
        raise AuditError(f"no existe la fuente: {path}")

    for member, data in iterator:
        findings.extend(inspect_bytes(source, member, data))
    return findings


def build_summary(sources: list[Path], findings: list[Finding]) -> dict[str, object]:
    official_by_source: dict[str, set[str]] = {}
    recoverable_hash_sources: dict[str, set[str]] = {}
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.classification] = counts.get(finding.classification, 0) + 1
        if finding.classification == "official_exact_asset":
            official_by_source.setdefault(finding.source, set()).add(finding.filename)
        if finding.classification == "recoverable_primary_logo" and finding.sha256:
            recoverable_hash_sources.setdefault(finding.sha256, set()).add(finding.source)

    complete_packages = sorted(
        source for source, names in official_by_source.items() if names == OFFICIAL
    )
    recoverable_primary = [
        {
            "sha256": hash_value,
            "independent_sources": sorted(source_names),
            "verified": len(source_names) >= 2,
        }
        for hash_value, source_names in sorted(recoverable_hash_sources.items())
    ]
    return {
        "sources": [str(path) for path in sources],
        "known_missing_package_names": sorted(
            name for name in KNOWN_PACKAGE_NAMES if not any(path.name == name for path in sources)
        ),
        "counts": counts,
        "complete_exact_packages": complete_packages,
        "recoverable_primary_candidates": recoverable_primary,
        "master_ready": bool(complete_packages),
        "policy": {
            "redraw_allowed": False,
            "derive_reversed_or_favicons": False,
            "archival_boards_are_logo_sources": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sources", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-exact-package", action="store_true")
    args = parser.parse_args()

    sources = [path.expanduser().resolve() for path in args.sources]
    findings: list[Finding] = []
    try:
        for source in sources:
            findings.extend(audit_source(source))
        report = {
            "summary": build_summary(sources, findings),
            "findings": [asdict(finding) for finding in findings],
        }
        rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        print(rendered, end="")
        if args.require_exact_package and not report["summary"]["master_ready"]:
            return 2
        return 0
    except (AuditError, OSError, UnicodeError) as exc:
        print(f"ERROR DE AUDITORÍA: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
