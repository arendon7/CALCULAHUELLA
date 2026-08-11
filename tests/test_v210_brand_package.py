import importlib.util
import stat
import struct
import sys
import zipfile
import zlib
from pathlib import Path

import pytest

pytestmark = pytest.mark.smoke
ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


audit = load_module("v210_audit_historical_sources", ROOT / "scripts" / "brand" / "audit_historical_sources.py")
importer = load_module("v210_import_master_package", ROOT / "scripts" / "brand" / "import_master_package.py")


def chunk(kind: bytes, payload: bytes) -> bytes:
    crc = zlib.crc32(kind)
    crc = zlib.crc32(payload, crc) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", crc)


def fake_png(width: int, height: int) -> bytes:
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return audit.PNG_SIGNATURE + chunk(b"IHDR", ihdr) + chunk(b"IEND", b"")


def complete_assets():
    return {
        "logo-oficial.png": fake_png(470, 195),
        "logo-oficial-blanco.png": fake_png(470, 195),
        "favicon-64.png": fake_png(64, 64),
        "favicon-256.png": fake_png(256, 256),
    }


def write_complete_zip(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in complete_assets().items():
            archive.writestr(f"static/img/brand/{name}", data)


def test_read_only_auditor_recognizes_only_complete_four_asset_package(tmp_path):
    package = tmp_path / "calcula_tu_huella_front_consolidado_v0_37.zip"
    write_complete_zip(package)

    findings = audit.audit_source(package)
    summary = audit.build_summary([package], findings)

    assert summary["master_ready"] is True
    assert summary["complete_exact_packages"] == [str(package)]
    assert summary["counts"]["official_exact_asset"] == 4
    assert summary["policy"] == {
        "redraw_allowed": False,
        "derive_reversed_or_favicons": False,
        "archival_boards_are_logo_sources": False,
    }


def test_auditor_never_promotes_legacy_svg_package(tmp_path):
    package = tmp_path / "legacy.zip"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("app/static/img/brand-primary.svg", "<svg/>")
        archive.writestr("app/static/img/brand-reversed.svg", "<svg/>")
        archive.writestr("app/static/img/brand-symbol.svg", "<svg/>")

    findings = audit.audit_source(package)
    summary = audit.build_summary([package], findings)

    assert summary["master_ready"] is False
    assert summary["counts"]["legacy_brand_asset"] == 3


def test_zip_path_traversal_and_symlinks_are_rejected(tmp_path):
    traversal = tmp_path / "traversal.zip"
    with zipfile.ZipFile(traversal, "w") as archive:
        archive.writestr("../logo-oficial.png", fake_png(470, 195))
    with pytest.raises(audit.AuditError, match="ruta insegura"):
        audit.audit_source(traversal)
    with pytest.raises(importer.MasterPackageError, match="Ruta insegura"):
        importer.load_exact_assets(traversal)

    linked = tmp_path / "linked.zip"
    info = zipfile.ZipInfo("static/img/brand/logo-oficial.png")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(linked, "w") as archive:
        archive.writestr(info, "../../outside.png")
    with pytest.raises(audit.AuditError, match="symlink"):
        audit.audit_source(linked)
    with pytest.raises(importer.MasterPackageError, match="Symlink"):
        importer.load_exact_assets(linked)


def test_importer_requires_all_four_assets_and_exact_dimensions(tmp_path):
    incomplete = tmp_path / "incomplete.zip"
    with zipfile.ZipFile(incomplete, "w") as archive:
        archive.writestr("logo-oficial.png", fake_png(470, 195))
    with pytest.raises(importer.MasterPackageError, match="Falta el activo oficial requerido"):
        importer.load_exact_assets(incomplete)

    complete = tmp_path / "complete.zip"
    write_complete_zip(complete)
    assets = importer.load_exact_assets(complete)
    inventory = importer.build_inventory(assets)

    assert set(assets) == set(importer.REQUIRED)
    assert inventory["logo-oficial.png"]["width"] == 470
    assert inventory["logo-oficial.png"]["height"] == 195
    assert inventory["favicon-64.png"]["width"] == 64
    assert inventory["favicon-256.png"]["width"] == 256
    assert all(len(item["sha256"]) == 64 for item in inventory.values())


def test_importer_rejects_corrupt_png_crc(tmp_path):
    assets = complete_assets()
    corrupt = bytearray(assets["logo-oficial.png"])
    corrupt[-1] ^= 0x01
    assets["logo-oficial.png"] = bytes(corrupt)

    with pytest.raises(importer.MasterPackageError, match="CRC inválido"):
        importer.build_inventory(assets)


def test_template_activation_plan_is_recursive_and_removes_legacy_aliases(tmp_path, monkeypatch):
    templates = tmp_path / "templates"
    nested = templates / "pages"
    nested.mkdir(parents=True)
    (templates / "base.html").write_text(
        "img/brand-primary.svg img/brand-reversed.svg img/brand-symbol.svg",
        encoding="utf-8",
    )
    (nested / "public.html").write_text(
        "img/logo.svg img/logo-white.svg img/favicon.svg",
        encoding="utf-8",
    )
    monkeypatch.setattr(importer, "TEMPLATES", templates)

    planned = importer.plan_template_updates()
    combined = "\n".join(planned.values())

    for legacy in importer.REFERENCE_REPLACEMENTS:
        assert legacy not in combined
    assert "img/brand/logo-oficial.png" in combined
    assert "img/brand/logo-oficial-blanco.png" in combined
    assert "img/brand/favicon-64.png" in combined
    assert nested / "public.html" in planned


def test_brand_tooling_contains_no_transform_or_extractall_path():
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            ROOT / "scripts" / "brand" / "audit_historical_sources.py",
            ROOT / "scripts" / "brand" / "import_master_package.py",
        )
    )
    forbidden = (
        "from PIL",
        "import PIL",
        ".resize(",
        ".thumbnail(",
        ".crop(",
        ".convert(",
        "ImageEnhance",
        "ImageOps",
        ".extractall(",
    )
    assert not any(token in source for token in forbidden)
    assert '"transformation": "none"' in source
