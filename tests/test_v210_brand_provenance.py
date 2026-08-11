import base64
import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.smoke

ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR_PATH = ROOT / "scripts" / "brand" / "extract_embedded_master.py"
VERIFIER_PATH = ROOT / "scripts" / "brand" / "verify_master_assets.py"
MANIFEST_PATH = ROOT / "app" / "static" / "img" / "brand-manifest.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


recovery = load_module("v210_extract_embedded_master", EXTRACTOR_PATH)
verifier = load_module("v210_verify_master_assets", VERIFIER_PATH)

# PNG transparente 1×1 usado solo como fixture técnico.
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9ZQmcAAAAASUVORK5CYII="
)


def html_with_png(data: bytes, alt: str = "Calcula tu Huella") -> str:
    payload = base64.b64encode(data).decode("ascii")
    return f'<html><body><img alt="{alt}" src="data:image/png;base64,{payload}"></body></html>'


def test_recovers_only_identical_copies_from_independent_html_sources(tmp_path):
    first = tmp_path / "v0_44_experiencia.html"
    second = tmp_path / "experiencia_interna.html"
    first.write_text(html_with_png(PNG_1X1), encoding="utf-8")
    second.write_text(html_with_png(PNG_1X1), encoding="utf-8")

    selected, data, candidates = recovery.select_exact_copy([first, second], 1, 1)

    assert data == PNG_1X1
    assert selected.width == 1
    assert selected.height == 1
    assert len(candidates) == 2
    assert len({candidate.sha256 for candidate in candidates}) == 1
    assert {candidate.source for candidate in candidates} == {
        "v0_44_experiencia.html",
        "experiencia_interna.html",
    }


def test_rejects_duplicate_path_as_false_independent_evidence(tmp_path):
    source = tmp_path / "duplicate.html"
    source.write_text(html_with_png(PNG_1X1), encoding="utf-8")

    with pytest.raises(recovery.EmbeddedLogoError, match="dos HTML históricos independientes"):
        recovery.select_exact_copy([source, source], 1, 1)


def test_rejects_truncated_or_wrong_dimension_payloads(tmp_path):
    truncated = tmp_path / "truncated.html"
    valid = tmp_path / "valid.html"
    truncated.write_text(
        '<img alt="Calcula tu Huella" src="data:image/png;base64,iVBORw0KGgo">',
        encoding="utf-8",
    )
    valid.write_text(html_with_png(PNG_1X1), encoding="utf-8")

    with pytest.raises(recovery.EmbeddedLogoError):
        recovery.select_exact_copy([truncated, valid], 1, 1)

    first = tmp_path / "size-a.html"
    second = tmp_path / "size-b.html"
    first.write_text(html_with_png(PNG_1X1), encoding="utf-8")
    second.write_text(html_with_png(PNG_1X1), encoding="utf-8")
    with pytest.raises(recovery.EmbeddedLogoError, match="No existe una copia"):
        recovery.select_exact_copy([first, second], 470, 195)


def test_extractor_is_byte_preserving_and_has_no_image_transforms():
    source = EXTRACTOR_PATH.read_text(encoding="utf-8")
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
    assert '"transformation": "none"' in source


def test_manifest_stops_misclassifying_legacy_svgs_as_canonical():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert "canonical_assets" not in manifest
    assert manifest["approved_master"]["status"] == verifier.RECOVERABLE_STATUS
    assert manifest["approved_master"]["expected_primary"] == {
        "filename": "logo-oficial.png",
        "width": 470,
        "height": 195,
        "encoding": "PNG data URI base64",
        "minimum_independent_sources": 2,
        "transformation": "none",
    }
    assert set(manifest["approved_master"]["pending_independent_assets"]) == {
        "logo-oficial-blanco.png",
        "favicon-64.png",
        "favicon-256.png",
    }
    assert all(
        item["status"] == "legacy_not_approved_master"
        for item in manifest["compatibility_assets"].values()
    )
    verifier.validate_contract(manifest)


def test_strict_master_gate_remains_closed_until_all_exact_pngs_exist():
    manifest = verifier.load_manifest()
    verifier.validate_contract(manifest)

    with pytest.raises(verifier.BrandValidationError, match="aún no está instalada"):
        verifier.validate_installed_assets(manifest)
