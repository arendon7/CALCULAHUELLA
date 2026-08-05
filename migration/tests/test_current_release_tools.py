import hashlib
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

EVIDENCE_CONTENT = b'{"tests": 337, "passed": true}\n'
EVIDENCE_SHA = hashlib.sha256(EVIDENCE_CONTENT).hexdigest()
VALIDATION_NAME = "VALIDACION_V1_0_0_FINAL.md"
MANIFEST_NAME = "MANIFIESTO_PAQUETE_V1_0_0_FINAL.txt"
ACT_NAME = "ACTA_CIERRE_V1_0_0.md"


def validation_text() -> str:
    return (
        "# Validación técnica · Calcula tu Huella V1.0.0 final\n"
        "337 pruebas recolectadas y aprobadas mediante procesos aislados.\n"
        "320 rutas FastAPI.\n"
        "112 modelos ORM.\n"
        "2 plantillas HTML compiladas.\n"
        "113 tablas físicas.\n"
        "Migración final: 20260805_0033.\n"
        "Versión final para despliegue controlado.\n"
    )


def shared_runtime() -> dict[str, bytes]:
    files: dict[str, bytes] = {
        "app/main.py": b"app = object()\n",
        "app/config.py": b'class Settings:\n    version: str = "1.0.0"\n',
        "migrations/env.py": b"# env\n",
        "migrations/versions/20260805_0033_final.py": (
            b"revision = '20260805_0033'\n"
        ),
        "alembic.ini": b"[alembic]\n",
        "run.py": b"print('ok')\n",
        "requirements.txt": b"fastapi\n",
        "tests/test_release.py": b"def test_ok(): assert True\n",
        "release/FINAL_TEST_EVIDENCE.json": EVIDENCE_CONTENT,
        "app/templates/a.html": b"<p>a</p>",
        "app/templates/b.html": b"<p>b</p>",
    }
    for asset in (
        "logo-oficial.png",
        "logo-oficial-blanco.png",
        "favicon-64.png",
        "favicon-256.png",
    ):
        files[f"app/static/img/brand/{asset}"] = b"png"
    return files


def inventory_manifest(files: dict[str, bytes], *, bad_hash=False) -> bytes:
    lines = [
        "CALCULA TU HUELLA V1.0.0 FINAL · MANIFIESTO",
        "Clasificación: despliegue controlado",
        f"Archivos inventariados: {len(files) + 1}",
        f"Mac: {sum(name.startswith('MAC/') for name in files)}",
        f"Windows: {sum(name.startswith('WINDOWS/') for name in files)}",
        "",
        "RUTA | BYTES | SHA-256",
    ]
    for name, data in sorted(files.items()):
        digest = hashlib.sha256(data).hexdigest()
        if bad_hash and name == "MAC/app/main.py":
            digest = "0" * 64
        lines.append(f"{name} | {len(data)} | {digest}")
    return ("\n".join(lines) + "\n").encode("utf-8")


def write_package(
    path: Path,
    *,
    wrapper=None,
    drift=False,
    forbidden=False,
    bad_inventory=False,
):
    files: dict[str, bytes] = {
        VALIDATION_NAME: validation_text().encode("utf-8"),
        ACT_NAME: b"V1.0.0 final para despliegue controlado\n",
    }
    runtime = shared_runtime()
    for root in ("MAC", "WINDOWS"):
        for name, content in runtime.items():
            data = content
            if drift and root == "WINDOWS" and name == "app/main.py":
                data = b"WINDOWS_DRIFT = True\n"
            files[f"{root}/{name}"] = data
        files[f"{root}/platform.txt"] = root.encode("utf-8")
    if forbidden:
        files["MAC/instance/demo.sqlite3"] = b"database"

    files[MANIFEST_NAME] = inventory_manifest(files, bad_hash=bad_inventory)
    prefix = f"{wrapper}/" if wrapper else ""
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(prefix + name, content)


def archive_names(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        names = [item.filename for item in archive.infolist() if not item.is_dir()]
    top = {Path(name).parts[0] for name in names}
    if len(top) == 1 and next(iter(top)) not in {"MAC", "WINDOWS"}:
        names = [Path(*Path(name).parts[1:]).as_posix() for name in names]
    return names


def contract_for(path: Path):
    names = archive_names(path)
    return {
        "release": "1.0.0",
        "display_release": "V1.0.0 FINAL",
        "status": "final_controlled_deployment_validated_pending_binary_import",
        "post_import_status": (
            "final_controlled_deployment_imported_pending_external_certification"
        ),
        "controlled_deployment_authorized": True,
        "public_production_authorized": False,
        "production_authorized": False,
        "archive": {
            "filename": path.name,
            "sha256": verifier.sha256_file(path),
            "inventory_total_files": len(names),
        },
        "distributions": {
            "MAC": {
                "inventory_files": sum(name.startswith("MAC/") for name in names),
                "minimum_files": sum(name.startswith("MAC/") for name in names),
            },
            "WINDOWS": {
                "inventory_files": sum(
                    name.startswith("WINDOWS/") for name in names
                ),
                "minimum_files": sum(
                    name.startswith("WINDOWS/") for name in names
                ),
            },
        },
        "runtime_contract": {
            "routes": 320,
            "jinja_templates": 2,
            "orm_models": 112,
            "physical_tables_after_migration": 113,
            "alembic_head": "20260805_0033",
        },
        "validation": {
            "suite_tests_passed": 337,
            "evidence_file": "release/FINAL_TEST_EVIDENCE.json",
            "evidence_sha256": EVIDENCE_SHA,
        },
        "required_documents": [VALIDATION_NAME, MANIFEST_NAME, ACT_NAME],
        "required_brand_assets": [
            "logo-oficial.png",
            "logo-oficial-blanco.png",
            "favicon-64.png",
            "favicon-256.png",
        ],
        "source_evidence": {},
    }


def test_verifier_accepts_direct_and_wrapped_final_packages(
    tmp_path, monkeypatch
):
    for wrapper in (None, "calcula_tu_huella_v1_0_0_final"):
        archive = tmp_path / ("wrapped.zip" if wrapper else "direct.zip")
        write_package(archive, wrapper=wrapper)
        monkeypatch.setattr(
            verifier, "load_contract", lambda p=archive: contract_for(p)
        )

        report = verifier.validate_archive(archive)

        assert report["release"] == "1.0.0"
        assert report["wrapper"] == wrapper
        assert report["inventory"]["verified_entries"] == 34
        assert report["inventory"]["self_reference_excluded"] is True
        assert report["mac"]["files"] == 16
        assert report["windows"]["files"] == 16


def test_verifier_rejects_inventory_mismatch(tmp_path, monkeypatch):
    archive = tmp_path / "bad-inventory.zip"
    write_package(archive, bad_inventory=True)
    monkeypatch.setattr(verifier, "load_contract", lambda: contract_for(archive))

    with pytest.raises(verifier.ReleaseError, match="Inventario físico inválido"):
        verifier.validate_archive(archive)


def test_verifier_rejects_core_drift_forbidden_data_and_wrong_zip_hash(
    tmp_path, monkeypatch
):
    drift = tmp_path / "drift.zip"
    write_package(drift, drift=True)
    monkeypatch.setattr(verifier, "load_contract", lambda: contract_for(drift))
    with pytest.raises(verifier.ReleaseError, match="divergente"):
        verifier.validate_archive(drift)

    forbidden = tmp_path / "forbidden.zip"
    write_package(forbidden, forbidden=True)
    monkeypatch.setattr(
        verifier, "load_contract", lambda: contract_for(forbidden)
    )
    with pytest.raises(verifier.ReleaseError, match="Contenido prohibido"):
        verifier.validate_archive(forbidden)

    wrong_hash = tmp_path / "wrong-hash.zip"
    write_package(wrong_hash)
    contract = contract_for(wrong_hash)
    contract["archive"]["sha256"] = "0" * 64
    monkeypatch.setattr(verifier, "load_contract", lambda: contract)
    with pytest.raises(verifier.ReleaseError, match="SHA-256 distinto"):
        verifier.validate_archive(wrong_hash)


def test_importer_preserves_governance_and_builds_controlled_overlay(tmp_path):
    for name in (".git", ".github", ".devcontainer", "migration"):
        (tmp_path / name).mkdir()
    (tmp_path / ".gitignore").write_text("instance/\n", encoding="utf-8")
    (tmp_path / ".gitattributes").write_text(
        "* text=auto\n", encoding="utf-8"
    )
    (tmp_path / "old").mkdir()
    importer.clear_runtime(tmp_path)
    assert not (tmp_path / "old").exists()
    assert all((tmp_path / name).exists() for name in importer.PRESERVE_TOP_LEVEL)

    mac = tmp_path / "mac"
    windows = tmp_path / "windows"
    repo = tmp_path / "repo"
    (mac / "app").mkdir(parents=True)
    (windows / "app").mkdir(parents=True)
    (mac / "app/same.py").write_text("same", encoding="utf-8")
    (windows / "app/same.py").write_text("same", encoding="utf-8")
    (windows / "app/windows.py").write_text("windows", encoding="utf-8")
    archive = tmp_path / "contract.zip"
    write_package(archive)

    result = importer.build_windows_overlay(
        mac, windows, repo, contract_for(archive)
    )

    assert result["files"] == 1
    manifest = json.loads(
        (repo / "platform/windows/OVERLAY_MANIFEST.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["files"][0]["path"] == "app/windows.py"
    assert manifest["controlled_deployment_authorized"] is True
    assert manifest["public_production_authorized"] is False
    assert manifest["production_authorized"] is False


def test_mark_imported_uses_final_status_without_authorizing_public_production(
    tmp_path,
):
    migration = tmp_path / "migration"
    migration.mkdir()
    archive = tmp_path / "release.zip"
    write_package(archive)
    contract = contract_for(archive)
    (migration / "current-release.json").write_text(
        json.dumps(contract), encoding="utf-8"
    )

    result = importer.mark_imported(tmp_path)

    assert result["status"] == (
        "final_controlled_deployment_imported_pending_external_certification"
    )
    assert result["controlled_deployment_authorized"] is True
    assert result["public_production_authorized"] is False
    assert result["production_authorized"] is False
    assert result["source_evidence"]["archive_imported_to_git"] is True
    assert result["source_evidence"]["runtime_matches_release"] is True
