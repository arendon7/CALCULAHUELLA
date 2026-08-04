import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VERIFIER_PATH = ROOT / "scripts" / "migration" / "verify_v049_archive.py"
IMPORTER_PATH = ROOT / "scripts" / "migration" / "import_v049_archive.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


verifier = load_module("verify_v049_archive", VERIFIER_PATH)
importer = load_module("import_v049_archive", IMPORTER_PATH)

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
        files[f"app/templates/template_{index:02d}.html"] = (
            landing if index == 0 else "<p>ok</p>"
        )
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
        "V049_LANDING_Y_CONVERSACION_FACTORES.md": "Landing técnica\n",
        "PROMPTS_LANDING_V049.md": "Prompts landing\n",
    }


def write_dual_archive(
    path: Path,
    *,
    wrapper=None,
    include_windows=True,
    mutate_windows=None,
    extra=None,
):
    prefix = f"{wrapper}/" if wrapper else ""
    mutate_windows = mutate_windows or {}
    extra = extra or {}
    core = shared_files()
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


def normalized_names(path: Path):
    with zipfile.ZipFile(path) as archive:
        names = [item.filename for item in archive.infolist() if not item.is_dir()]
    top = {Path(name).parts[0] for name in names}
    if len(top) == 1 and next(iter(top)) not in {"MAC", "WINDOWS"}:
        names = [Path(*Path(name).parts[1:]).as_posix() for name in names]
    return names


def contract_for(path: Path):
    names = normalized_names(path)
    return {
        "release": "0.49.0",
        "archive": {"sha256": verifier.sha256_file(path)},
        "package": {"required_roots": ["MAC", "WINDOWS"]},
        "distributions": {
            "MAC": {
                "physical_files": sum(name.startswith("MAC/") for name in names)
            },
            "WINDOWS": {
                "physical_files": sum(
                    name.startswith("WINDOWS/") for name in names
                )
            },
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


def test_verifier_accepts_direct_and_wrapped_packages(tmp_path, monkeypatch):
    for wrapper in (None, "calcula_tu_huella_v0_49_0_dual_mac_windows"):
        archive = tmp_path / ("wrapped.zip" if wrapper else "direct.zip")
        write_dual_archive(archive, wrapper=wrapper)
        monkeypatch.setattr(verifier, "load_contract", lambda p=archive: contract_for(p))

        report = verifier.validate_archive(archive)

        assert report["status"] == "verified_exact_dual_archive"
        assert report["package_wrapper"] == wrapper
        assert report["safe_to_stage"] is True


def test_verifier_allows_platform_scripts_but_rejects_core_drift(
    tmp_path, monkeypatch
):
    valid = tmp_path / "platform.zip"
    write_dual_archive(valid)
    monkeypatch.setattr(verifier, "load_contract", lambda: contract_for(valid))
    report = verifier.validate_archive(valid)
    paths = {item["path"] for item in report["windows_overlay"]}
    assert "scripts/platform_lifecycle.txt" in paths
    assert "ABRIR_CALCULA_TU_HUELLA.bat" in paths

    drift = tmp_path / "drift.zip"
    write_dual_archive(
        drift,
        mutate_windows={"app/main.py": "WINDOWS_DRIFT = True\n"},
    )
    monkeypatch.setattr(verifier, "load_contract", lambda: contract_for(drift))
    with pytest.raises(verifier.VerificationError, match="núcleo compartido"):
        verifier.validate_archive(drift)


def test_verifier_rejects_missing_distribution_database_and_hash(
    tmp_path, monkeypatch
):
    mac_only = tmp_path / "mac-only.zip"
    write_dual_archive(mac_only, include_windows=False)
    monkeypatch.setattr(verifier, "load_contract", lambda: contract_for(mac_only))
    with pytest.raises(verifier.VerificationError, match="MAC/ y WINDOWS/"):
        verifier.validate_archive(mac_only)

    with_db = tmp_path / "with-db.zip"
    write_dual_archive(
        with_db,
        extra={"MAC/instance/demo.sqlite3": b"database"},
    )
    monkeypatch.setattr(verifier, "load_contract", lambda: contract_for(with_db))
    with pytest.raises(verifier.VerificationError, match="Contenido prohibido"):
        verifier.validate_archive(with_db)

    wrong_hash = tmp_path / "wrong-hash.zip"
    write_dual_archive(wrong_hash)
    contract = contract_for(wrong_hash)
    contract["archive"]["sha256"] = "0" * 64
    monkeypatch.setattr(verifier, "load_contract", lambda: contract)
    with pytest.raises(verifier.VerificationError, match="SHA-256 distinto"):
        verifier.validate_archive(wrong_hash)


def test_importer_locates_package_and_builds_minimal_overlay(tmp_path):
    direct = tmp_path / "direct"
    (direct / "MAC").mkdir(parents=True)
    (direct / "WINDOWS").mkdir()
    package, wrapper = importer.locate_package_root(direct)
    assert package == direct
    assert wrapper is None

    wrapped_root = tmp_path / "wrapped"
    wrapped = wrapped_root / "release"
    (wrapped / "MAC").mkdir(parents=True)
    (wrapped / "WINDOWS").mkdir()
    package, wrapper = importer.locate_package_root(wrapped_root)
    assert package == wrapped
    assert wrapper == "release"

    mac = tmp_path / "mac-tree"
    windows = tmp_path / "windows-tree"
    repo = tmp_path / "repo"
    (mac / "app").mkdir(parents=True)
    (windows / "app").mkdir(parents=True)
    (windows / "scripts").mkdir(parents=True)
    (mac / "app/same.py").write_text("same\n", encoding="utf-8")
    (windows / "app/same.py").write_text("same\n", encoding="utf-8")
    (mac / "app/changed.py").write_text("mac\n", encoding="utf-8")
    (windows / "app/changed.py").write_text("windows\n", encoding="utf-8")
    (windows / "scripts/start.bat").write_text("@echo off\n", encoding="utf-8")

    result = importer.build_windows_overlay(mac, windows, repo)
    assert result["files"] == 2
    assert not (repo / "platform/windows/overlay/app/same.py").exists()
    manifest = json.loads(
        (repo / "platform/windows/OVERLAY_MANIFEST.json").read_text(
            encoding="utf-8"
        )
    )
    assert {item["path"] for item in manifest["files"]} == {
        "app/changed.py",
        "scripts/start.bat",
    }


def test_importer_preserves_governance_and_checks_runtime(tmp_path):
    for directory in (".git", ".github", ".devcontainer", "migration"):
        (tmp_path / directory).mkdir()
    (tmp_path / ".gitignore").write_text("instance/\n", encoding="utf-8")
    (tmp_path / ".gitattributes").write_text("* text=auto\n", encoding="utf-8")
    (tmp_path / "old-app").mkdir()
    importer.clear_managed_tree(tmp_path)
    for preserved in importer.PRESERVE_TOP_LEVEL:
        assert (tmp_path / preserved).exists()
    assert not (tmp_path / "old-app").exists()

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
    for name in BRAND:
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
