from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/package-mac-selfcontained.yml"
PACKAGING = ROOT / "packaging/mac"
LOCK = ROOT / "requirements-lock.txt"

ARM64_SHA = "25baa97c65b3f0aa90e21131b4f9e80aef8899e8144006db8a9d2c1ab9e807e3"
X86_64_SHA = "127053f1736f721e391ddb46f07585d05756e15bb8d757d3bbc0519738998ba1"


def test_v200_mac_package_uses_immutable_runtime_and_hashed_lock() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    lock = LOCK.read_text(encoding="utf-8")

    assert "integration/workflow-v1.5.0" not in workflow
    assert "releases/latest" not in workflow
    assert 'PYTHON_RUNTIME_VERSION: "3.12.13"' in workflow
    assert 'PYTHON_BUILD_STANDALONE_TAG: "20260807"' in workflow
    assert ARM64_SHA in workflow
    assert X86_64_SHA in workflow
    assert "sha256sum -c -" in workflow
    assert "requirements-lock.txt" in workflow
    assert "--require-hashes" in workflow
    assert "pip install --upgrade pip" not in workflow
    assert "--hash=sha256:" in lock
    assert "botocore==" in lock
    assert "starlette==" in lock


def test_v200_mac_wheelhouses_share_modern_macos_11_floor() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "--platform macosx_11_0_arm64" in workflow
    assert "--platform macosx_11_0_x86_64" in workflow
    assert "macosx_10_13_x86_64" not in workflow


def test_v200_mac_package_excludes_non_runtime_ci_and_test_sources() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "--exclude '.github/'" in workflow
    assert "--exclude 'tests/'" in workflow
    assert "--exclude 'packaging/'" in workflow


def test_v200_mac_package_has_verifiable_provenance_and_deterministic_archive_check() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "BUILD_PROVENANCE.json" in workflow
    assert "RELEASE_MANIFEST.json" in workflow
    assert "MANIFEST_SHA256.txt" in workflow
    assert "WHEELHOUSE_SHA256.txt" in workflow
    assert "GITHUB_SHA" in workflow
    assert "source_commit" in workflow
    assert "zip -X -q -y" in workflow
    assert ".rebuild.zip" in workflow
    assert 'cmp ".pack/${VERSION_DIR}.zip" ".pack/${VERSION_DIR}.rebuild.zip"' in workflow


def test_v200_mac_launchers_are_versioned_and_shell_valid() -> None:
    names = (
        "1_INSTALAR_Y_ABRIR_DEMO.command",
        "2_ABRIR_DEMO.command",
        "3_CERRAR_DEMO.command",
        "4_REINICIAR_DATOS_DEMO.command",
        "5_VERIFICAR_INSTALACION.command",
    )
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert 'cat > "$ROOT/1_INSTALAR_Y_ABRIR_DEMO.command"' not in workflow

    for name in names:
        path = PACKAGING / name
        assert path.is_file(), f"Falta launcher versionado: {name}"
        result = subprocess.run(
            ["/bin/bash", "-n", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"{name}: {result.stderr}"


def test_v200_installer_verifies_package_and_installs_only_hashed_offline_dependencies() -> None:
    installer = (PACKAGING / "1_INSTALAR_Y_ABRIR_DEMO.command").read_text(encoding="utf-8")
    verifier = (PACKAGING / "5_VERIFICAR_INSTALACION.command").read_text(encoding="utf-8")

    assert "/usr/bin/shasum -a 256 -c MANIFEST_SHA256.txt" in installer
    assert "--no-index" in installer
    assert "--require-hashes" in installer
    assert "requirements-lock.txt" in installer
    assert "BUILD_PROVENANCE.json" in installer
    assert "BUILD_PROVENANCE.json" in verifier
