import importlib.util
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "migration" / "verify_v048_archive.py"
MODULE_NAME = "verify_v048_archive"

spec = importlib.util.spec_from_file_location(MODULE_NAME, MODULE_PATH)
assert spec and spec.loader
verifier = importlib.util.module_from_spec(spec)
sys.modules[MODULE_NAME] = verifier
spec.loader.exec_module(verifier)

LOGICAL_HASH = "91410e981bf93e2c036cf544cc190dc57c39f5c464e1793cea314b4b7d210eef"


def contract_for(archive: Path):
    return {
        "archive": {"sha256": verifier.sha256(archive)},
        "source_tree": {
            "logical_sha256": LOGICAL_HASH,
            "jinja_templates": 65,
            "test_files": 31,
        },
        "required_brand_assets": [
            "logo-oficial.png",
            "logo-oficial-blanco.png",
            "favicon-64.png",
            "favicon-256.png",
        ],
        "required_module_assets": [
            "01_dashboard_climatico.png",
            "02_calidad_de_datos.png",
            "08_metodologia_y_alcances.png",
        ],
        "minimum_module_pngs": 8,
    }


def write_valid_archive(path: Path, *, version: str = "0.48.0", extra=None):
    extra = extra or {}
    with zipfile.ZipFile(path, "w") as archive:
        root = "calcula_tu_huella_v0_48_0_portafolio_reduccion_mac"
        archive.writestr(f"{root}/app/main.py", "app = object()\n")
        archive.writestr(f"{root}/app/config.py", f'class Settings:\n    version: str = "{version}"\n')
        archive.writestr(f"{root}/alembic.ini", "[alembic]\n")
        archive.writestr(f"{root}/run.py", "print('ok')\n")
        archive.writestr(f"{root}/requirements.txt", "fastapi\n")
        for index in range(65):
            archive.writestr(f"{root}/app/templates/template_{index:02d}.html", "<p>ok</p>")
        for index in range(31):
            archive.writestr(f"{root}/tests/test_{index:02d}.py", "def test_ok(): assert True\n")
        for name in (
            "logo-oficial.png",
            "logo-oficial-blanco.png",
            "favicon-64.png",
            "favicon-256.png",
        ):
            archive.writestr(f"{root}/app/static/img/brand/{name}", b"png")
        module_names = [
            "01_dashboard_climatico.png",
            "02_calidad_de_datos.png",
            "03_inventario.png",
            "04_calculo.png",
            "05_reduccion.png",
            "06_reportes.png",
            "07_territorios.png",
            "08_metodologia_y_alcances.png",
        ]
        for name in module_names:
            archive.writestr(f"{root}/app/static/img/modules/{name}", b"png")
        manifest = (
            "Versión de aplicación: 0.48.0.\n"
            "406 archivos funcionales inventariados.\n"
            f"SHA-256 lógico del árbol: {LOGICAL_HASH}.\n"
        )
        archive.writestr(f"{root}/MANIFIESTO_V0_48_0.txt", manifest)
        for name, content in extra.items():
            archive.writestr(f"{root}/{name}", content)


def test_accepts_archive_that_satisfies_v048_contract(tmp_path, monkeypatch):
    archive = tmp_path / "v048.zip"
    write_valid_archive(archive)
    monkeypatch.setattr(verifier, "load_contract", lambda: contract_for(archive))

    report = verifier.validate_archive(archive)

    assert report["status"] == "verified_exact_archive"
    assert report["jinja_templates"] == 65
    assert report["test_files"] == 31
    assert report["module_pngs"] == 8
    assert report["safe_to_stage"] is True


def test_rejects_wrong_application_version(tmp_path, monkeypatch):
    archive = tmp_path / "old.zip"
    write_valid_archive(archive, version="0.47.0")
    monkeypatch.setattr(verifier, "load_contract", lambda: contract_for(archive))

    with pytest.raises(verifier.VerificationError, match="no declara la versión 0.48.0"):
        verifier.validate_archive(archive)


def test_rejects_local_database_inside_archive(tmp_path, monkeypatch):
    archive = tmp_path / "with-db.zip"
    write_valid_archive(archive, extra={"instance/demo.sqlite3": b"database"})
    monkeypatch.setattr(verifier, "load_contract", lambda: contract_for(archive))

    with pytest.raises(verifier.VerificationError, match="Contenido prohibido"):
        verifier.validate_archive(archive)


def test_rejects_modified_archive_hash(tmp_path, monkeypatch):
    archive = tmp_path / "modified.zip"
    write_valid_archive(archive)
    contract = contract_for(archive)
    contract["archive"]["sha256"] = "0" * 64
    monkeypatch.setattr(verifier, "load_contract", lambda: contract)

    with pytest.raises(verifier.VerificationError, match="SHA-256 del ZIP distinto"):
        verifier.validate_archive(archive)
