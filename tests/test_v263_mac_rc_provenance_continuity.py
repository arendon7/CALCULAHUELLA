from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_WORKFLOW = ROOT / ".github" / "workflows" / "package-mac-selfcontained.yml"
LEGACY_RC_WORKFLOW = ROOT / ".github" / "workflows" / "package-mac-v215-rc.yml"

ARM64_SHA = "25baa97c65b3f0aa90e21131b4f9e80aef8899e8144006db8a9d2c1ab9e807e3"
X86_64_SHA = "127053f1736f721e391ddb46f07585d05756e15bb8d757d3bbc0519738998ba1"


def _workflow_source() -> str:
    return PACKAGE_WORKFLOW.read_text(encoding="utf-8")


def test_v263_expired_artifact_rc1_workflow_is_retired() -> None:
    assert not LEGACY_RC_WORKFLOW.exists()

    source = _workflow_source()
    assert "workflow_dispatch:" in source
    assert "BASE_ARTIFACT_ID" not in source
    assert "/actions/artifacts/" not in source
    assert "base_runtime_artifact_id" not in source
    assert "runtime_and_wheelhouse_reused_unchanged" not in source


def test_v263_mac_candidate_rebuilds_pinned_runtime_and_locked_wheelhouses() -> None:
    source = _workflow_source()

    assert 'PYTHON_RUNTIME_VERSION: "3.12.13"' in source
    assert 'PYTHON_BUILD_STANDALONE_TAG: "20260807"' in source
    assert ARM64_SHA in source
    assert X86_64_SHA in source
    assert "python-build-standalone/releases/download/${PYTHON_BUILD_STANDALONE_TAG}" in source
    assert source.count("sha256sum -c -") >= 2
    assert source.count("--require-hashes") >= 3
    assert "--platform macosx_11_0_arm64" in source
    assert "--platform macosx_11_0_x86_64" in source


def test_v263_mac_candidate_binds_artifact_to_source_and_dependency_provenance() -> None:
    source = _workflow_source()

    for required in (
        "BUILD_PROVENANCE.json",
        "RELEASE_MANIFEST.json",
        "MANIFEST_SHA256.txt",
        "WHEELHOUSE_SHA256.txt",
        "requirements_lock_sha256",
        "wheelhouse_manifest_sha256",
        "source_commit",
        "source_ref",
        "GITHUB_SHA",
    ):
        assert required in source

    assert "zip -X -q -y" in source
    assert ".rebuild.zip" in source
    assert 'cmp ".pack/${VERSION_DIR}.zip" ".pack/${VERSION_DIR}.rebuild.zip"' in source


def test_v263_mac_candidate_keeps_physical_uat_build_deliberate() -> None:
    source = _workflow_source()

    # The current canonical candidate is produced deliberately by dispatch after
    # exact-head adoption; source_commit in the manifest is the dispatched SHA.
    assert "workflow_dispatch:" in source
    assert "source_commit" in source
    assert '"workflow_run_id": os.environ["GITHUB_RUN_ID"]' in source
    assert "retention-days: 14" in source
