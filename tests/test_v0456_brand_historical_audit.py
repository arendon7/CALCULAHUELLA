import base64
import importlib.util
import struct
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "brand" / "audit_historical_sources.py"
MODULE_NAME = "audit_historical_sources"

spec = importlib.util.spec_from_file_location(MODULE_NAME, MODULE_PATH)
assert spec and spec.loader
audit = importlib.util.module_from_spec(spec)
sys.modules[MODULE_NAME] = audit
spec.loader.exec_module(audit)


def fake_png(width: int, height: int) -> bytes:
    ihdr = struct.pack(">I", 13) + b"IHDR" + struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return audit.PNG_SIGNATURE + ihdr + b"\x00\x00\x00\x00" + b"\x00\x00\x00\x00IEND\xaeB`\x82"


def html_with_png(data: bytes) -> bytes:
    encoded = base64.b64encode(data)
    return b'<img alt="Calcula tu Huella" src="data:image/png;base64,' + encoded + b'">'


def test_identifies_complete_exact_master_package(tmp_path):
    package = tmp_path / "calcula_tu_huella_front_consolidado_v0_37.zip"
    assets = {
        "logo-oficial.png": fake_png(470, 195),
        "logo-oficial-blanco.png": fake_png(470, 195),
        "favicon-64.png": fake_png(64, 64),
        "favicon-256.png": fake_png(256, 256),
    }
    with zipfile.ZipFile(package, "w") as archive:
        for name, data in assets.items():
            archive.writestr(f"static/img/brand/{name}", data)

    findings = audit.audit_source(package)
    summary = audit.build_summary([package], findings)

    assert summary["master_ready"] is True
    assert summary["complete_exact_packages"] == [str(package)]
    assert summary["counts"]["official_exact_asset"] == 4


def test_legacy_svg_archive_is_never_master_ready(tmp_path):
    package = tmp_path / "calcula_tu_huella_v0_45_2_completa_mac.zip"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr(
            "app/static/img/brand-primary.svg",
            '<svg><text>Plataforma profesional de huella de carbono</text></svg>',
        )
        archive.writestr("app/static/img/brand-reversed.svg", "<svg/>")
        archive.writestr("app/static/img/brand-symbol.svg", "<svg/>")

    findings = audit.audit_source(package)
    summary = audit.build_summary([package], findings)

    assert summary["master_ready"] is False
    assert summary["counts"]["legacy_brand_asset"] == 3
    primary = next(item for item in findings if item.filename == "brand-primary.svg")
    assert "descriptor anterior" in primary.note


def test_verifies_same_embedded_primary_across_independent_html_sources(tmp_path):
    logo = fake_png(470, 195)
    first = tmp_path / "v0_44_experiencia.html"
    second = tmp_path / "experiencia_interna.html"
    first.write_bytes(html_with_png(logo))
    second.write_bytes(html_with_png(logo))

    findings = audit.audit_source(first) + audit.audit_source(second)
    summary = audit.build_summary([first, second], findings)

    candidates = summary["recoverable_primary_candidates"]
    assert len(candidates) == 1
    assert candidates[0]["verified"] is True
    assert candidates[0]["independent_sources"] == sorted([str(first), str(second)])
    assert summary["master_ready"] is False


def test_archival_board_is_reference_not_logo_source(tmp_path):
    board = tmp_path / "01_identidad_visual.png"
    board.write_bytes(fake_png(1600, 1000))

    findings = audit.audit_source(board)

    assert len(findings) == 1
    assert findings[0].classification == "archival_visual_reference"
    assert "no autoriza" in findings[0].note


def test_rejects_zip_path_traversal(tmp_path):
    package = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("../logo-oficial.png", fake_png(470, 195))

    with pytest.raises(audit.AuditError, match="ruta insegura"):
        audit.audit_source(package)


def test_auditor_contains_no_image_transformation_operations():
    source = MODULE_PATH.read_text(encoding="utf-8")
    forbidden = (
        "from PIL",
        "import PIL",
        ".resize(",
        ".thumbnail(",
        ".crop(",
        ".convert(",
        "ImageEnhance",
        "ImageOps",
    )
    assert not any(token in source for token in forbidden)
