#!/usr/bin/env python3
"""Audita fuentes históricas de marca sin instalar ni transformar activos."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import re
import stat
import struct
import zipfile
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Iterator

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
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
DATA_URI = re.compile(rb"data:image/png;base64,(?P<payload>[A-Za-z0-9+/=\r\n\t ]+)", re.I)
MAX_MEMBER_BYTES = 25 * 1024 * 1024
MAX_TOTAL_BYTES = 150 * 1024 * 1024


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
    if not data.startswith(PNG_SIGNATURE):
        raise AuditError("contenido PNG inválido")
    offset = len(PNG_SIGNATURE)
    width = height = None
    seen_ihdr = False
    seen_iend = False
    while offset < len(data):
        if offset + 12 > len(data):
            raise AuditError("PNG truncado")
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        chunk_start = offset + 8
        chunk_end = chunk_start + length
        crc_end = chunk_end + 4
        if crc_end > len(data):
            raise AuditError("PNG truncado")
        payload = data[chunk_start:chunk_end]
        expected_crc = struct.unpack(">I", data[chunk_end:crc_end])[0]
        actual_crc = zlib.crc32(chunk_type)
        actual_crc = zlib.crc32(payload, actual_crc) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise AuditError("PNG con CRC inválido")
        if not seen_ihdr:
            if chunk_type != b"IHDR" or length != 13:
                raise AuditError("PNG sin IHDR inicial válido")
            width, height = struct.unpack(">II", payload[:8])
            if width < 1 or height < 1:
                raise AuditError("PNG con dimensiones inválidas")
            seen_ihdr = True
        if chunk_type == b"IEND":
            if length != 0 or crc_end != len(data):
                raise AuditError("PNG con IEND inválido o datos posteriores")
            seen_iend = True
            break
        offset = crc_end
    if not seen_ihdr or not seen_iend or width is None or height is None:
        raise AuditError("PNG incompleto")
    return width, height


def classify_named_file(source: str, member: str, data: bytes) -> list[Finding]:
    name = Path(member).name
    if name in OFFICIAL:
        width, height = png_metadata(data)
        return [Finding(source, member, "official_exact_asset", name, digest(data), len(data), width, height,
                        "activo exacto por nombre; requiere cotejo conjunto del paquete")]
    if name in LEGACY_NAMES:
        note = "compatibilidad legacy; prohibido promover a Marca Maestra"
        if b"Plataforma profesional de huella de carbono" in data:
            note += "; contiene descriptor anterior"
        return [Finding(source, member, "legacy_brand_asset", name, digest(data), len(data), note=note)]
    if name in ARCHIVAL_VISUAL_NAMES:
        width = height = None
        try:
            width, height = png_metadata(data)
        except AuditError:
            pass
        return [Finding(source, member, "archival_visual_reference", name, digest(data), len(data), width, height,
                        "puede orientar UX; no autoriza recorte ni extracción de logo")]
    return []


def embedded_png_findings(source: str, member: str, data: bytes) -> list[Finding]:
    if not member.lower().endswith((".html", ".htm")):
        return []
    findings: list[Finding] = []
    for occurrence, match in enumerate(DATA_URI.finditer(data), start=1):
        payload = re.sub(rb"\s+", b"", match.group("payload"))
        try:
            decoded = base64.b64decode(payload, validate=True)
            width, height = png_metadata(decoded)
        except (ValueError, binascii.Error, AuditError):
            findings.append(Finding(source, member, "invalid_embedded_png", f"embedded-png-{occurrence}",
                                    note="data URI inválido o truncado"))
            continue
        classification = "recoverable_primary_logo" if (width, height) == (470, 195) else "embedded_png_reference"
        findings.append(Finding(source, member, classification, f"embedded-png-{occurrence}", digest(decoded),
                                len(decoded), width, height, "sin transformación"))
    return findings


def inspect_bytes(source: str, member: str, data: bytes) -> list[Finding]:
    return classify_named_file(source, member, data) + embedded_png_findings(source, member, data)


def iter_directory(root: Path) -> Iterator[tuple[str, bytes]]:
    total = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        size = path.stat().st_size
        if size > MAX_MEMBER_BYTES:
            continue
        total += size
        if total > MAX_TOTAL_BYTES:
            raise AuditError("la fuente excede el límite total de auditoría")
        yield path.relative_to(root).as_posix(), path.read_bytes()


def safe_zip_members(archive: zipfile.ZipFile) -> Iterator[tuple[str, bytes]]:
    total = 0
    for item in archive.infolist():
        if item.is_dir():
            continue
        normalized = Path(item.filename)
        mode = (item.external_attr >> 16) & 0xFFFF
        if normalized.is_absolute() or ".." in normalized.parts:
            raise AuditError(f"ruta insegura dentro del ZIP: {item.filename}")
        if stat.S_ISLNK(mode):
            raise AuditError(f"symlink no permitido dentro del ZIP: {item.filename}")
        if item.file_size > MAX_MEMBER_BYTES:
            continue
        total += item.file_size
        if total > MAX_TOTAL_BYTES:
            raise AuditError("el ZIP excede el límite total descomprimido")
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
        if path.is_symlink():
            raise AuditError(f"symlink no permitido: {path}")
        if path.stat().st_size > MAX_MEMBER_BYTES:
            raise AuditError(f"archivo demasiado grande para auditoría: {path}")
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
    complete_packages = sorted(source for source, names in official_by_source.items() if names == OFFICIAL)
    recoverable_primary = [
        {"sha256": value, "independent_sources": sorted(names), "verified": len(names) >= 2}
        for value, names in sorted(recoverable_hash_sources.items())
    ]
    return {
        "sources": [str(path) for path in sources],
        "known_missing_package_names": sorted(name for name in KNOWN_PACKAGE_NAMES if not any(path.name == name for path in sources)),
        "counts": counts,
        "complete_exact_packages": complete_packages,
        "recoverable_primary_candidates": recoverable_primary,
        "master_ready": bool(complete_packages),
        "policy": {"redraw_allowed": False, "derive_reversed_or_favicons": False, "archival_boards_are_logo_sources": False},
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
        report = {"summary": build_summary(sources, findings), "findings": [asdict(item) for item in findings]}
        rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        print(rendered, end="")
        return 2 if args.require_exact_package and not report["summary"]["master_ready"] else 0
    except (AuditError, OSError, UnicodeError) as exc:
        print(f"ERROR DE AUDITORÍA: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
