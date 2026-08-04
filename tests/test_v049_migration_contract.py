import importlib.util
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "migration" / "verify_v049_archive.py"
MODULE_NAME = "verify_v049_archive"

spec = importlib.util.spec_from_file_location(MODULE_NAME, MODULE_PATH)
assert spec and spec.loader
verifier = importlib.util.module_from_spec(spec)
sys.modules[MODULE_NAME] = verifier
spec.loader.exec_module(verifier)

BRAND = (
    "logo-oficial.png",
    "logo-oficial-blanco.png",
    "favicon-64.png",
    "favicon-256.png",
)
MODULES = (
    "01_dashboard_climatico.png",
    "02_calidad_de_datos.png",
    "03_inventario.png",
    "04_calculo.png",
    "05_reduccion.png",
    "06_reportes.png",
    "07_territorios.png",
    "08_metodologia_y_alcances.png",
)


def shared_files():
    files = {
        "app/main.py": "app = object()\n",
        "app/config.py": 'class Settings:\n    version: str = "0.49.0"\n',
        "app/models.py": (
            "class ActivityFactorSelection: pass\n"
            "activity_factor_selections = True\n"
        ),
        "alembic.ini": "[alembic]\n",
        "run.py": "print('ok')\n",
        "requirements.txt": "fastapi\n",
        "requirements-dev.txt": "pytest\n",
        "Dockerfile": "FROM python:3.12-slim\n",
        "migrations/env.py": "# env\n",
        "migrations/versions/20260804_0030_activity_factor_selections.py": (
            "revision = '20260804_0030'\n"
        ),
        "tests/test_v049.py": "def test_ok(): assert True\n",
    }
    landing = (
        "Potenciado por Greenatics · Huella Esencial · Gestión de Carbono · "
        "Gestión Avanzada y Verificación"
    )
    for index in range(65):
        content = landing if index == 0 else "<p>ok</p>"
        files[f"app/templates/template_{index:02d}.html"] = content
    for name in BRAND:
        files[f"app/static/img/brand/{name}"] = b"png"
    for name in MODULES:
        files[f"app/static/img/modules/{name}"] = b"png"
    return files


def package_documents():
    return {
        "00_LEEME_PRIMERO.txt": "V0.49.0\n",
        "MANIFIESTO_PAQUETE_V0_49_0.txt": (
            "V0.49.0\n"
            "MAC: 424 archivos físicos; 413 archivos funcionales\n"
            "WINDOWS: 401 archivos físicos; 390 archivos funcionales\n"
            "Modelos ORM: 110\n"
            "Rutas totales: 287\n"
            "Migración desde base vacía hasta 20260804_0030\n"
            "115 pruebas aprobadas\n"
        ),
        "VALIDACION_V0_49.md": (
            "ActivityFactorSelection\nactivity_factor_selections\n"
            "20260804_0030\n115 pruebas aprobadas\n"
        ),
        "V049_LANDING_Y_CONVERSACION_FACTORES.md": (
            "Landing y conversación técnica\n"
        ),
        "PROMPTS_LANDING_V049.md": "Prompts landing\n",
    }


def write_dual_archive(
    path: Path,
    *,
    mutate_windows=None,
    extra=None,
    include_windows=True,
    wrapper=None,
):
    mutate_windows = mutate_windows or {}
    extra = extra or {}
    core = shared_files()
    prefix = f"{wrapper}/" if wrapper else ""
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in package_documents().items():
            archive.writestr(prefix + name, content)
        for relative, content in core.items():
            archive.writestr(f"{prefix}MAC/{relative}", content)
        archive.writestr(
            f"{prefix}MAC/scripts/platform_lifecycle.txt",
            "mac lifecycle\n",
        )
        archive.writestr(
            f"{prefix}MAC/ABRIR_CALCULA_TU_HUELLA.command",
            "#!/bin/bash\n",
        )
        if include_windows:
            for relative, content in core.items():
                archive.writestr(
                    f"{prefix}WINDOWS/{relative}",
                    mutate_windows.get(relative, content),
                )
            archive.writestr(
                f"{prefix}WINDOWS/scripts/platform_lifecycle.txt",
                "windows lifecycle\n",
            )
            archive.writestr(
                f"{prefix}WINDOWS/ABRIR_CALCULA_TU_HUELLA.bat",
                "@echo off\r\n",
            )
        for relative, content in extra.items():
            archive.writestr(prefix + relative, content)


def normalized_names(archive: Path):
    with zipfile.ZipFile(archive) as z:
        names = [item.filename for item in z.infolist() if not item.is_dir()]
    first_parts = {Path(name).parts[0] for name in names}
    if len(first_parts) == 1:
        first = next(iter(first_parts))
        if first not in {"MAC", "WINDOWS"}:
            names = [Path(*Path(name).parts[1:]).as_posix() for name in names]
    return names


def contract_for(archive: Path):
    names = normalized_names(archive)
    mac_count = sum(name.startswith("MAC/") for name in names)
    windows_count = sum(name.startswith("WINDOWS/") for name in names)
    return {
        "release": "0.49.0",
        "archive": {"sha256": verifier.sha256_file(archive)},
        "package": {"required_roots": ["MAC", "WINDOWS"]},
        "distributions": {
            "MAC": {"physical_files": mac_count},
            "WINDOWS": {"physical_files": windows_count},
        },
        "runtime": {"jinja_templates": 65},
        "required_root_documents": list(package_documents()),
        "required_brand_assets": list(BRAND),
        "required_module_assets": [
            "01_dashboard_climatico.png",
            "02_calidad_de_datos.png",
            "08_metodologia_y_alcances.png",
        ],
        "minimum_module_pngs": 8,
    }


def test_accepts_exact_dual_package(tmp_path, monkeypatch):
    archive = tmp_path / "v049.zip"
    write_dual_archive(archive)
    monkeypatch.setattr(verifier, "load_contract", lambda: contract_for(archive))

    report = verifier.validate_archive(archive)

    assert report["status"] == "verified_exact_dual_archive"
    assert report["release"] == "0.49.0"
    assert report["package_wrapper"] is None
    assert report["mac"]["templates"] == 65
    assert report["windows"]["templates"] == 65
    assert report["shared_core"]["shared_files"] > 70
    assert report["windows_overlay_files"] == 2
    assert report["safe_to_stage"] is True


def test_accepts_single_package_wrapper(tmp_path, monkeypatch):
    archive = tmp_path / "wrapped.zip"
    write_dual_archive(
        archive,
        wrapper="calcula_tu_huella_v0_49_0_dual_mac_windows",
    )
    monkeypatch.setattr(verifier, "load_contract", lambda: contract_for(archive))

    report = verifier.validate_archive(archive)

    assert report["package_wrapper"] == (
        "calcula_tu_huella_v0_49_0_dual_mac_windows"
    )
    assert report["safe_to_stage"] is True


def test_platform_scripts_may_differ_without_core_drift(tmp_path, monkeypatch):
    archive = tmp_path / "platform-scripts.zip"
    write_dual_archive(archive)
    monkeypatch.setattr(verifier, "load_contract", lambda: contract_for(archive))

    report = verifier.validate_archive(archive)

    overlay_paths = {item["path"] for item in report["windows_overlay"]}
    assert "scripts/platform_lifecycle.txt" in overlay_paths
    assert "ABRIR_CALCULA_TU_HUELLA.bat" in overlay_paths


def test_rejects_changed_shared_core(tmp_path, monkeypatch):
    archive = tmp_path / "drift.zip"
    write_dual_archive(
        archive,
        mutate_windows={
            "app/main.py": "app = object()\nWINDOWS_DRIFT = True\n"
        },
    )
    monkeypatch.setattr(verifier, "load_contract", lambda: contract_for(archive))

    with pytest.raises(verifier.VerificationError, match="núcleo compartido"):
        verifier.validate_archive(archive)


def test_rejects_missing_windows_distribution(tmp_path, monkeypatch):
    archive = tmp_path / "mac-only.zip"
    write_dual_archive(archive, include_windows=False)
    contract = contract_for(archive)
    contract["distributions"]["WINDOWS"]["physical_files"] = 0
    monkeypatch.setattr(verifier, "load_contract", lambda: contract)

    with pytest.raises(
        verifier.VerificationError,
        match="Falta la distribución WINDOWS",
    ):
        verifier.validate_archive(archive)


def test_rejects_database_inside_package(tmp_path, monkeypatch):
    archive = tmp_path / "with-db.zip"
    write_dual_archive(
        archive,
        extra={"MAC/instance/demo.sqlite3": b"database"},
    )
    monkeypatch.setattr(verifier, "load_contract", lambda: contract_for(archive))

    with pytest.raises(verifier.VerificationError, match="Contenido prohibido"):
        verifier.validate_archive(archive)


def test_rejects_modified_archive_hash(tmp_path, monkeypatch):
    archive = tmp_path / "modified.zip"
    write_dual_archive(archive)
    contract = contract_for(archive)
    contract["archive"]["sha256"] = "0" * 64
    monkeypatch.setattr(verifier, "load_contract", lambda: contract)

    with pytest.raises(verifier.VerificationError, match="SHA-256 distinto"):
        verifier.validate_archive(archive)
