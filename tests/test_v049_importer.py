import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "migration" / "import_v049_archive.py"
MODULE_NAME = "import_v049_archive"

spec = importlib.util.spec_from_file_location(MODULE_NAME, MODULE_PATH)
assert spec and spec.loader
importer = importlib.util.module_from_spec(spec)
sys.modules[MODULE_NAME] = importer
spec.loader.exec_module(importer)


def test_locates_direct_dual_package(tmp_path):
    (tmp_path / "MAC").mkdir()
    (tmp_path / "WINDOWS").mkdir()

    package, wrapper = importer.locate_package_root(tmp_path)

    assert package == tmp_path
    assert wrapper is None


def test_locates_single_wrapped_dual_package(tmp_path):
    wrapped = tmp_path / "calcula_tu_huella_v0_49_0_dual_mac_windows"
    (wrapped / "MAC").mkdir(parents=True)
    (wrapped / "WINDOWS").mkdir()

    package, wrapper = importer.locate_package_root(tmp_path)

    assert package == wrapped
    assert wrapper == wrapped.name


def test_rejects_ambiguous_extracted_layout(tmp_path):
    (tmp_path / "one").mkdir()
    (tmp_path / "two").mkdir()

    with pytest.raises(importer.ImportErrorV049, match="única carpeta superior"):
        importer.locate_package_root(tmp_path)


def test_windows_overlay_contains_only_differences(tmp_path):
    mac = tmp_path / "MAC"
    windows = tmp_path / "WINDOWS"
    repo = tmp_path / "repo"
    (mac / "app").mkdir(parents=True)
    (windows / "app").mkdir(parents=True)
    (windows / "scripts").mkdir(parents=True)
    (mac / "app" / "same.py").write_text("same\n", encoding="utf-8")
    (windows / "app" / "same.py").write_text("same\n", encoding="utf-8")
    (mac / "app" / "changed.py").write_text("mac\n", encoding="utf-8")
    (windows / "app" / "changed.py").write_text("windows\n", encoding="utf-8")
    (windows / "scripts" / "start.bat").write_text("@echo off\n", encoding="utf-8")

    result = importer.build_windows_overlay(mac, windows, repo)

    assert result["files"] == 2
    assert not (repo / "platform/windows/overlay/app/same.py").exists()
    assert (repo / "platform/windows/overlay/app/changed.py").read_text(
        encoding="utf-8"
    ) == "windows\n"
    assert (repo / "platform/windows/overlay/scripts/start.bat").is_file()

    manifest = json.loads(
        (repo / "platform/windows/OVERLAY_MANIFEST.json").read_text(
            encoding="utf-8"
        )
    )
    entries = {item["path"]: item for item in manifest["files"]}
    assert entries["app/changed.py"]["windows_only"] is False
    assert entries["scripts/start.bat"]["windows_only"] is True


def test_clear_managed_tree_preserves_github_governance(tmp_path):
    for directory in (".git", ".github", ".devcontainer", "migration"):
        (tmp_path / directory).mkdir()
    (tmp_path / ".gitignore").write_text("instance/\n", encoding="utf-8")
    (tmp_path / ".gitattributes").write_text("* text=auto\n", encoding="utf-8")
    (tmp_path / "app").mkdir()
    (tmp_path / "README.md").write_text("old\n", encoding="utf-8")

    importer.clear_managed_tree(tmp_path)

    for preserved in importer.PRESERVE_TOP_LEVEL:
        assert (tmp_path / preserved).exists()
    assert not (tmp_path / "app").exists()
    assert not (tmp_path / "README.md").exists()


def test_post_import_checks_require_complete_runtime(tmp_path):
    (tmp_path / "app/templates").mkdir(parents=True)
    (tmp_path / "app/static/img/brand").mkdir(parents=True)
    (tmp_path / "migrations/versions").mkdir(parents=True)
    (tmp_path / "platform/windows").mkdir(parents=True)
    (tmp_path / "app/config.py").write_text(
        'version: str = "0.49.0"\n', encoding="utf-8"
    )
    for index in range(65):
        (tmp_path / "app/templates" / f"template_{index:02d}.html").write_text(
            "<p>ok</p>", encoding="utf-8"
        )
    for name in (
        "logo-oficial.png",
        "logo-oficial-blanco.png",
        "favicon-64.png",
        "favicon-256.png",
    ):
        (tmp_path / "app/static/img/brand" / name).write_bytes(b"png")
    (tmp_path / "migrations/versions/20260804_0030_selection.py").write_text(
        "revision = '20260804_0030'\n", encoding="utf-8"
    )
    (tmp_path / "platform/windows/OVERLAY_MANIFEST.json").write_text(
        '{"files": []}\n', encoding="utf-8"
    )

    report = importer.post_import_checks(tmp_path)

    assert report["version"] == "0.49.0"
    assert report["templates"] == 65
    assert report["brand_assets"] == 4
