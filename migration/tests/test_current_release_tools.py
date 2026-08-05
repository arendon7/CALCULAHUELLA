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


verifier = load(
    "verify_current_release",
    ROOT / "scripts/migration/verify_current_release.py",
)
importer = load(
    "import_current_release",
    ROOT / "scripts/migration/import_current_release.py",
)

EVIDENCE_SHA = "evidence-sha"


def contract_for(path: Path, *, manifest_name="MANIFIESTO_ENTREGA.txt"):
    return {
        "release": "1.0.0-rc1",
        "archive": {
            "filename": path.name,
            "sha256": verifier.sha256_file(path),
        },
        "distributions": {
            "MAC": {"functional_files": 13, "tree_sha256": "mac-tree"},
            "WINDOWS": {
                "functional_files": 13,
                "tree_sha256": "windows-tree",
            },
        },
        "runtime_contract": {
            "routes": 315,
            "jinja_templates": 2,
            "orm_models": 112,
            "physical_tables_after_migration": 113,
            "alembic_head": "20260805_0032",
        },
        "validation": {
            "evidence_file": "release/RC1_TEST_EVIDENCE.json",
            "evidence_sha256": EVIDENCE_SHA,
        },
        "required_documents": [
            "VALIDACION_RELEASE.md",
            manifest_name,
            "V100_RC1_ESTABILIZACION_Y_LANZAMIENTO.md",
        ],
        "required_brand_assets": [
            "logo-oficial.png",
            "logo-oficial-blanco.png",
            "favicon-64.png",
            "favicon-256.png",
        ],
    }


def valid_manifest() -> str:
    return (
        "CALCULA TU HUELLA V1.0.0-RC1\n"
        "Rutas: 315.\n"
        "Modelos ORM: 112.\n"
        "Plantillas HTML: 2.\n"
        "Tablas físicas desde base vacía: 113.\n"
        "Cabeza Alembic: 20260805_0032.\n"
        f"Evidencia SHA-256: {EVIDENCE_SHA}.\n"
        "MAC árbol SHA-256 mac-tree.\n"
        "WINDOWS árbol SHA-256 windows-tree.\n"
    )


def write_package(
    path: Path,
    *,
    wrapper=None,
    drift=False,
    forbidden=False,
    manifest=None,
    manifest_name="MANIFIESTO_ENTREGA.txt",
):
    prefix = f"{wrapper}/" if wrapper else ""
    shared = {
        "app/main.py": "app = object()\n",
        "app/config.py": 'version: str = "1.0.0-rc1"\n',
        "migrations/env.py": "# env\n",
        "migrations/versions/20260805_0032_release.py": (
            "revision = '20260805_0032'\n"
        ),
        "alembic.ini": "[alembic]\n",
        "run.py": "print('ok')\n",
        "requirements.txt": "fastapi\n",
        "tests/test_release.py": "def test_ok(): assert True\n",
        "release/RC1_TEST_EVIDENCE.json": '{"passed": true}\n',
        "app/templates/a.html": "<p>a</p>",
        "app/templates/b.html": "<p>b</p>",
    }
    for asset in (
        "logo-oficial.png",
        "logo-oficial-blanco.png",
        "favicon-64.png",
        "favicon-256.png",
    ):
        shared[f"app/static/img/brand/{asset}"] = b"png"

    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(prefix + "VALIDACION_RELEASE.md", "validated")
        archive.writestr(
            prefix + "V100_RC1_ESTABILIZACION_Y_LANZAMIENTO.md",
            "scope frozen",
        )
        archive.writestr(
            prefix + manifest_name,
            manifest if manifest is not None else valid_manifest(),
        )
        for root in ("MAC", "WINDOWS"):
            for name, content in shared.items():
                if drift and root == "WINDOWS" and name == "app/main.py":
                    content = "drift = True\n"
                archive.writestr(f"{prefix}{root}/{name}", content)
            archive.writestr(f"{prefix}{root}/platform.txt", root)
        if forbidden:
            archive.writestr(prefix + "MAC/instance/demo.sqlite3", b"db")


def test_verifier_accepts_rc1_metrics_in_label_first_format(
    tmp_path, monkeypatch
):
    for wrapper in (None, "release"):
        archive = tmp_path / ("wrapped.zip" if wrapper else "direct.zip")
        write_package(archive, wrapper=wrapper)
        monkeypatch.setattr(
            verifier,
            "load_contract",
            lambda p=archive: contract_for(p),
        )

        report = verifier.validate_archive(archive)

        assert report["release"] == "1.0.0-rc1"
        assert report["wrapper"] == wrapper
        assert report["manifest"] == "MANIFIESTO_ENTREGA.txt"
        assert report["core"]["shared_files"] >= 11


def test_verifier_accepts_number_first_metric_format(tmp_path, monkeypatch):
    archive = tmp_path / "number-first.zip"
    manifest = (
        "V1.0.0-RC1\n"
        "315 rutas\n2 plantillas Jinja\n112 modelos ORM\n"
        "113 tablas físicas\n20260805_0032\n"
        f"{EVIDENCE_SHA}\nmac-tree\nwindows-tree\n"
    )
    write_package(archive, manifest=manifest)
    monkeypatch.setattr(
        verifier,
        "load_contract",
        lambda: contract_for(archive),
    )

    assert verifier.validate_archive(archive)["release"] == "1.0.0-rc1"


def test_verifier_rejects_unlabeled_manifest_metrics(tmp_path, monkeypatch):
    archive = tmp_path / "unlabeled.zip"
    write_package(
        archive,
        manifest=(
            "1.0.0-rc1 315 2 112 113 20260805_0032 "
            f"{EVIDENCE_SHA} mac-tree windows-tree"
        ),
    )
    monkeypatch.setattr(
        verifier,
        "load_contract",
        lambda: contract_for(archive),
    )

    with pytest.raises(verifier.ReleaseError, match="métrica etiquetada"):
        verifier.validate_archive(archive)


def test_verifier_rejects_missing_evidence_hash(tmp_path, monkeypatch):
    archive = tmp_path / "missing-evidence.zip"
    write_package(
        archive,
        manifest=valid_manifest().replace(EVIDENCE_SHA, "other"),
    )
    monkeypatch.setattr(
        verifier,
        "load_contract",
        lambda: contract_for(archive),
    )

    with pytest.raises(verifier.ReleaseError, match="SHA-256 de evidencia"):
        verifier.validate_archive(archive)


def test_verifier_rejects_hash_core_drift_and_database(
    tmp_path, monkeypatch
):
    archive = tmp_path / "release.zip"
    write_package(archive, drift=True)
    monkeypatch.setattr(
        verifier,
        "load_contract",
        lambda: contract_for(archive),
    )
    with pytest.raises(verifier.ReleaseError, match="divergente"):
        verifier.validate_archive(archive)

    database = tmp_path / "database.zip"
    write_package(database, forbidden=True)
    monkeypatch.setattr(
        verifier,
        "load_contract",
        lambda: contract_for(database),
    )
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
    (tmp_path / ".gitattributes").write_text(
        "* text=auto\n", encoding="utf-8"
    )
    (tmp_path / "old").mkdir()

    importer.clear_runtime(tmp_path)

    assert not (tmp_path / "old").exists()
    assert all(
        (tmp_path / name).exists() for name in importer.PRESERVE_TOP_LEVEL
    )

    mac = tmp_path / "mac"
    windows = tmp_path / "windows"
    repo = tmp_path / "repo"
    (mac / "app").mkdir(parents=True)
    (windows / "app").mkdir(parents=True)
    (mac / "app/same.py").write_text("same", encoding="utf-8")
    (windows / "app/same.py").write_text("same", encoding="utf-8")
    (windows / "app/windows.py").write_text("windows", encoding="utf-8")

    result = importer.build_windows_overlay(mac, windows, repo)

    assert result["files"] == 1
    manifest = json.loads(
        (repo / "platform/windows/OVERLAY_MANIFEST.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["files"][0]["path"] == "app/windows.py"
