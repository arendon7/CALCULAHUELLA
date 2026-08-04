import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


verifier = load("verify_current_release", ROOT / "scripts/migration/verify_current_release.py")
importer = load("import_current_release", ROOT / "scripts/migration/import_current_release.py")


def contract_for(path: Path):
    return {
        "release": "0.52.0",
        "archive": {"filename": path.name, "sha256": verifier.sha256_file(path)},
        "distributions": {
            "MAC": {"functional_files": 12, "tree_sha256": "mac-tree"},
            "WINDOWS": {"functional_files": 12, "tree_sha256": "windows-tree"},
        },
        "runtime_contract": {
            "routes": 298,
            "jinja_templates": 2,
            "orm_models": 111,
            "physical_tables_after_migration": 112,
            "alembic_head": "20260804_0031",
        },
        "required_documents": ["VALIDACION_V0_52.md", "MANIFIESTO_PAQUETE_V0_52_0.txt"],
        "required_brand_assets": ["logo-oficial.png", "logo-oficial-blanco.png", "favicon-64.png", "favicon-256.png"],
    }


def write_package(path: Path, *, wrapper=None, drift=False, forbidden=False):
    prefix = f"{wrapper}/" if wrapper else ""
    manifest = "0.52.0 298 68 111 112 20260804_0031 mac-tree windows-tree"
    shared = {
        "app/main.py": "app = object()\n",
        "app/config.py": 'version: str = "0.52.0"\n',
        "migrations/env.py": "# env\n",
        "migrations/versions/20260804_0031_onboarding.py": "revision = '20260804_0031'\n",
        "alembic.ini": "[alembic]\n",
        "run.py": "print('ok')\n",
        "requirements.txt": "fastapi\n",
        "tests/test_release.py": "def test_ok(): assert True\n",
        "app/templates/a.html": "<p>a</p>",
        "app/templates/b.html": "<p>b</p>",
    }
    for asset in ("logo-oficial.png", "logo-oficial-blanco.png", "favicon-64.png", "favicon-256.png"):
        shared[f"app/static/img/brand/{asset}"] = b"png"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(prefix + "VALIDACION_V0_52.md", "validated")
        archive.writestr(prefix + "MANIFIESTO_PAQUETE_V0_52_0.txt", manifest)
        for root in ("MAC", "WINDOWS"):
            for name, content in shared.items():
                if drift and root == "WINDOWS" and name == "app/main.py":
                    content = "drift = True\n"
                archive.writestr(f"{prefix}{root}/{name}", content)
            archive.writestr(f"{prefix}{root}/platform.txt", root)
        if forbidden:
            archive.writestr(prefix + "MAC/instance/demo.sqlite3", b"db")


def test_verifier_accepts_direct_and_wrapped_packages(tmp_path, monkeypatch):
    for wrapper in (None, "release"):
        archive = tmp_path / ("wrapped.zip" if wrapper else "direct.zip")
        write_package(archive, wrapper=wrapper)
        monkeypatch.setattr(verifier, "load_contract", lambda p=archive: contract_for(p))
        report = verifier.validate_archive(archive)
        assert report["release"] == "0.52.0"
        assert report["wrapper"] == wrapper
        assert report["core"]["shared_files"] >= 10


def test_verifier_rejects_hash_core_drift_and_database(tmp_path, monkeypatch):
    archive = tmp_path / "release.zip"
    write_package(archive, drift=True)
    monkeypatch.setattr(verifier, "load_contract", lambda: contract_for(archive))
    with pytest.raises(verifier.ReleaseError, match="divergente"):
        verifier.validate_archive(archive)

    database = tmp_path / "database.zip"
    write_package(database, forbidden=True)
    monkeypatch.setattr(verifier, "load_contract", lambda: contract_for(database))
    with pytest.raises(verifier.ReleaseError, match="prohibido"):
        verifier.validate_archive(database)

    clean = tmp_path / "clean.zip"
    write_package(clean)
    contract = contract_for(clean)
    contract["archive"]["sha256"] = "0" * 64
    monkeypatch.setattr(verifier, "load_contract", lambda: contract)
    with pytest.raises(verifier.ReleaseError, match="SHA-256"):
        verifier.validate_archive(clean)


def test_importer_preserves_governance_and_builds_overlay(tmp_path):
    for name in (".git", ".github", ".devcontainer", "migration"):
        (tmp_path / name).mkdir()
    (tmp_path / ".gitignore").write_text("instance/\n", encoding="utf-8")
    (tmp_path / ".gitattributes").write_text("* text=auto\n", encoding="utf-8")
    (tmp_path / "old").mkdir()
    importer.clear_runtime(tmp_path)
    assert not (tmp_path / "old").exists()
    assert all((tmp_path / name).exists() for name in importer.PRESERVE_TOP_LEVEL)

    mac, windows, repo = tmp_path / "mac", tmp_path / "windows", tmp_path / "repo"
    (mac / "app").mkdir(parents=True)
    (windows / "app").mkdir(parents=True)
    (mac / "app/same.py").write_text("same", encoding="utf-8")
    (windows / "app/same.py").write_text("same", encoding="utf-8")
    (windows / "app/windows.py").write_text("windows", encoding="utf-8")
    result = importer.build_windows_overlay(mac, windows, repo)
    assert result["files"] == 1
    manifest = json.loads((repo / "platform/windows/OVERLAY_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["files"][0]["path"] == "app/windows.py"
