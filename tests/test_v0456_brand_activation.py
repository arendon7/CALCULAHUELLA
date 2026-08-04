import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
IMPORTER_PATH = ROOT / "scripts" / "brand" / "import_master_package.py"
VERIFIER_PATH = ROOT / "scripts" / "brand" / "verify_master_assets.py"
MODULE_NAME = "import_master_package"

spec = importlib.util.spec_from_file_location(MODULE_NAME, IMPORTER_PATH)
assert spec and spec.loader
importer = importlib.util.module_from_spec(spec)
sys.modules[MODULE_NAME] = importer
spec.loader.exec_module(importer)


def sample_inventory():
    metadata = {
        "sha256": "a" * 64,
        "bytes": 123,
        "width": 470,
        "height": 195,
        "bit_depth": 8,
        "color_type": 2,
        "has_alpha": False,
    }
    return {
        "logo-oficial.png": metadata,
        "logo-oficial-blanco.png": {**metadata, "sha256": "b" * 64},
        "favicon-64.png": {**metadata, "sha256": "c" * 64, "width": 64, "height": 64},
        "favicon-256.png": {**metadata, "sha256": "d" * 64, "width": 256, "height": 256},
    }


def test_manifest_assets_match_strict_verifier_contract():
    assets = importer.manifest_assets(sample_inventory())

    assert set(assets) == {"logo_primary", "logo_reversed", "favicon_64", "favicon_256"}
    assert assets["logo_primary"]["path"] == "app/static/img/brand/logo-oficial.png"
    assert assets["logo_reversed"]["path"] == "app/static/img/brand/logo-oficial-blanco.png"
    assert assets["favicon_64"]["path"] == "app/static/img/brand/favicon-64.png"
    assert assets["favicon_256"]["path"] == "app/static/img/brand/favicon-256.png"

    verifier = VERIFIER_PATH.read_text(encoding="utf-8")
    importer_source = IMPORTER_PATH.read_text(encoding="utf-8")
    assert 'INSTALLED_STATUS = "installed_exact_master"' in verifier
    assert '"status": "installed_exact_master"' in importer_source
    for key in ("logo_primary", "logo_reversed", "favicon_64", "favicon_256"):
        assert f'"{key}"' in verifier


def test_template_plan_replaces_all_active_legacy_references(tmp_path, monkeypatch):
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "base.html").write_text(
        "img/brand-primary.svg img/brand-reversed.svg img/brand-symbol.svg",
        encoding="utf-8",
    )
    (templates / "public_base.html").write_text(
        "img/brand-primary.svg img/brand-symbol.svg",
        encoding="utf-8",
    )
    monkeypatch.setattr(importer, "TEMPLATES", templates)

    planned = importer.plan_template_updates()
    combined = "\n".join(planned.values())

    assert "brand-primary.svg" not in combined
    assert "brand-reversed.svg" not in combined
    assert "brand-symbol.svg" not in combined
    assert "img/brand/logo-oficial.png" in combined
    assert "img/brand/logo-oficial-blanco.png" in combined
    assert "img/brand/favicon-64.png" in combined


def test_template_plan_fails_when_required_official_usage_is_missing(tmp_path, monkeypatch):
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "base.html").write_text("<main>Sin recursos de marca</main>", encoding="utf-8")
    monkeypatch.setattr(importer, "TEMPLATES", templates)

    with pytest.raises(importer.MasterPackageError, match="no referencia el activo oficial"):
        importer.plan_template_updates()


def test_importer_contains_no_image_transformation_library():
    source = IMPORTER_PATH.read_text(encoding="utf-8")
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
