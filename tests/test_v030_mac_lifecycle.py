from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAC_INSTALLER = PROJECT_ROOT / "INSTALAR_O_ACTUALIZAR_CALCULA_TU_HUELLA.command"
MAC_ONLY = pytest.mark.skipif(not MAC_INSTALLER.is_file(), reason="Prueba exclusiva del paquete macOS")


@MAC_ONLY
def test_v030_installer_test_mode_creates_stable_install_and_cleans_legacy(tmp_path: Path) -> None:
    home = tmp_path / "home"
    downloads = home / "Downloads"
    desktop = home / "Desktop"
    applications = home / "Applications"
    install_root = home / "Library" / "Application Support" / "CalculaTuHuella"
    trash = home / ".Trash"
    for path in (downloads, desktop, applications, trash):
        path.mkdir(parents=True, exist_ok=True)

    legacy = downloads / "calcula_tu_huella_v0_29_completa_mac"
    (legacy / "app").mkdir(parents=True)
    (legacy / "instance" / "uploads").mkdir(parents=True)
    (legacy / "run.py").write_text("# legacy\n", encoding="utf-8")
    (legacy / "alembic.ini").write_text("[alembic]\n", encoding="utf-8")
    (legacy / "instance" / "calculatuhuella_v029.db").write_bytes(b"legacy-db")
    (legacy / "instance" / "uploads" / "evidencia.txt").write_text("soporte", encoding="utf-8")
    old_zip = downloads / "calcula_tu_huella_v0_29_completa_mac.zip"
    old_zip.write_bytes(b"old zip")
    current_zip = downloads / "calcula_tu_huella_v1_0_0_preparacion_productiva_dual_mac_windows.zip"
    current_zip.write_bytes(b"current zip")

    env = os.environ.copy()
    env.update(
        {
            "HOME": str(home),
            "CTH_INSTALL_ROOT": str(install_root),
            "CTH_APPLICATIONS_DIR": str(applications),
            "CTH_DESKTOP_DIR": str(desktop),
            "CTH_LEGACY_SEARCH_ROOTS": str(downloads),
            "CTH_TRASH_DIR": str(trash),
            "CTH_TEST_MODE": "1",
            "CTH_SKIP_START": "1",
            "CTH_NO_PAUSE": "1",
            "TERM": "dumb",
        }
    )
    result = subprocess.run(
        ["/bin/bash", str(PROJECT_ROOT / "INSTALAR_O_ACTUALIZAR_CALCULA_TU_HUELLA.command")],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr

    code_dir = install_root / "current"
    assert (code_dir / "app").is_dir()
    assert (code_dir / "ABRIR_CALCULA_TU_HUELLA.command").is_file()
    assert (applications / "Calcula tu Huella.app").is_dir()
    assert (desktop / "ABRIR CALCULA TU HUELLA.command").is_file()

    receipt = json.loads((install_root / "installation.json").read_text(encoding="utf-8"))
    assert receipt["version"] == "1.0.0"
    assert receipt["data_dir"] == str(install_root / "data")

    assert not legacy.exists()
    assert not old_zip.exists()
    assert current_zip.exists()
    assert any(path.name.startswith("calcula_tu_huella_v0_29_completa_mac_") for path in trash.iterdir())
    assert any(path.name.startswith("calcula_tu_huella_v0_29_completa_mac.zip_") for path in trash.iterdir())
    assert list((install_root / "backups").glob("calcula_tu_huella_v0_29_completa_mac_*.tar.gz"))
    assert (install_root / "data" / "uploads" / "evidencia.txt").read_text(encoding="utf-8") == "soporte"


@MAC_ONLY
def test_v030_shell_entrypoints_are_valid() -> None:
    # The V1.0 canonical package replaced the historical
    # 6_ENSAYAR_RESTAURACION.command wrapper with restore_mac.sh. Validate the
    # actual canonical lifecycle entrypoints instead of recreating a legacy file.
    scripts = [
        "INSTALAR_O_ACTUALIZAR_CALCULA_TU_HUELLA.command",
        "ABRIR_CALCULA_TU_HUELLA.command",
        "1_INSTALAR_Y_ABRIR.command",
        "2_ABRIR_CALCULA_TU_HUELLA.command",
        "3_DETENER_CALCULA_TU_HUELLA.command",
        "4_VER_ESTADO.command",
        "restore_mac.sh",
        "install_mac.sh",
        "start_mac.sh",
        "scripts/mac_lifecycle_common.sh",
        "scripts/easy_mac_common.sh",
    ]
    for relative in scripts:
        path = PROJECT_ROOT / relative
        assert path.is_file(), f"Falta entrypoint canónico: {relative}"
        result = subprocess.run(
            ["/bin/bash", "-n", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"{relative}: {result.stderr}"