#!/usr/bin/env python3
"""Recupera el logo principal exacto desde demos HTML autocontenidas.

El proyecto conservó varias copias del mismo PNG como data URI. Este comando
extrae esas copias, exige que sean idénticas, valida el PNG y solo entonces
permite escribir ``logo-oficial.png``. No redibuja, recolorea, recorta ni deriva
variantes.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import struct
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "app" / "static" / "img" / "brand" / "logo-oficial.png"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
DATA_URI = re.compile(r"^data:image/png;base64,(?P<payload>[A-Za-z0-9+/=\s]+)$", re.I)


class EmbeddedLogoError(RuntimeError):
    """La recuperación no satisface el contrato de marca."""


@dataclass(frozen=True)
class Candidate:
    source: str
    occurrence: int
    sha256: str
    bytes: int
    width: int
    height: int
    bit_depth: int
    color_type: int
    has_alpha: bool


class LogoDataUriParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "img":
            return
        values = {key.lower(): value or "" for key, value in attrs}
        source = values.get("src", "").strip()
        alt = values.get("alt", "").strip().casefold()
        if source.lower().startswith("data:image/png;base64,") and (
            "calcula tu huella" in alt or not alt
        ):
            self.sources.append(source)


def decode_data_uri(value: str) -> bytes:
    match = DATA_URI.fullmatch(value.strip())
    if not match:
        raise EmbeddedLogoError("Data URI PNG inválido")
    payload = re.sub(r"\s+", "", match.group("payload"))
    try:
        return base64.b64decode(payload, validate=True)
    except ValueError as exc:
        raise EmbeddedLogoError("Base64 inválido o truncado") from exc


def inspect_png(data: bytes) -> dict[str, int | bool]:
    if len(data) < 33 or not data.startswith(PNG_SIGNATURE) or data[12:16] != b"IHDR":
        raise EmbeddedLogoError("El contenido recuperado no es un PNG válido")
    width, height, bit_depth, color_type = struct.unpack(">IIBB", data[16:26])
    if width < 1 or height < 1:
        raise EmbeddedLogoError("El PNG tiene dimensiones inválidas")
    if not data.endswith(b"IEND\xaeB`\x82"):
        raise EmbeddedLogoError("El PNG está truncado: falta el cierre IEND")
    return {
        "width": width,
        "height": height,
        "bit_depth": bit_depth,
        "color_type": color_type,
        "has_alpha": color_type in {4, 6} or b"tRNS" in data,
    }


def extract_candidates(path: Path) -> list[tuple[Candidate, bytes]]:
    parser = LogoDataUriParser()
    parser.feed(path.read_text(encoding="utf-8"))
    results: list[tuple[Candidate, bytes]] = []
    for occurrence, source in enumerate(parser.sources, start=1):
        data = decode_data_uri(source)
        metadata = inspect_png(data)
        results.append(
            (
                Candidate(
                    source=path.name,
                    occurrence=occurrence,
                    sha256=hashlib.sha256(data).hexdigest(),
                    bytes=len(data),
                    **metadata,
                ),
                data,
            )
        )
    return results


def select_exact_copy(
    sources: list[Path], expected_width: int, expected_height: int
) -> tuple[Candidate, bytes, list[Candidate]]:
    unique_sources = list(dict.fromkeys(path.resolve() for path in sources))
    if len(unique_sources) < 2:
        raise EmbeddedLogoError("Se requieren al menos dos HTML históricos independientes")

    recovered: list[tuple[Candidate, bytes]] = []
    for source in unique_sources:
        if not source.is_file():
            raise EmbeddedLogoError(f"No existe la fuente: {source}")
        candidates = extract_candidates(source)
        if not candidates:
            raise EmbeddedLogoError(f"{source.name} no contiene el logo PNG embebido")
        recovered.extend(candidates)

    matching = [
        item
        for item in recovered
        if item[0].width == expected_width and item[0].height == expected_height
    ]
    if not matching:
        dimensions = sorted({(item[0].width, item[0].height) for item in recovered})
        raise EmbeddedLogoError(
            f"No existe una copia de {expected_width} × {expected_height}; encontradas: {dimensions}"
        )

    hashes = {candidate.sha256 for candidate, _ in matching}
    if len(hashes) != 1:
        details = ", ".join(
            f"{candidate.source}#{candidate.occurrence}:{candidate.sha256}"
            for candidate, _ in matching
        )
        raise EmbeddedLogoError(f"Las copias del logo no son idénticas: {details}")

    independent_sources = {candidate.source for candidate, _ in matching}
    if len(independent_sources) < 2:
        raise EmbeddedLogoError("El mismo PNG debe existir en dos archivos independientes")

    representative, data = matching[0]
    return representative, data, [candidate for candidate, _ in matching]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sources", nargs="+", type=Path, help="HTML autocontenidos históricos")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--expected-width", type=int, default=470)
    parser.add_argument("--expected-height", type=int, default=195)
    parser.add_argument("--apply", action="store_true", help="Escribir el PNG recuperado")
    args = parser.parse_args()

    try:
        representative, data, candidates = select_exact_copy(
            [path.expanduser().resolve() for path in args.sources],
            args.expected_width,
            args.expected_height,
        )
        report = {
            "selected": asdict(representative),
            "verified_copies": [asdict(candidate) for candidate in candidates],
            "verified_independent_sources": sorted({candidate.source for candidate in candidates}),
            "transformation": "none",
            "output": str(args.output),
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if not args.apply:
            print("Validación completada. Usa --apply para materializar logo-oficial.png.")
            return 0

        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)
        provenance = output.with_suffix(".provenance.json")
        provenance.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Logo principal exacto recuperado: {output}")
        return 0
    except (EmbeddedLogoError, OSError, UnicodeError) as exc:
        print(f"ERROR DE RECUPERACIÓN: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
