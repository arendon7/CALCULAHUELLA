from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from app.observability import release_commit_from_environment

ROOT = Path(__file__).resolve().parents[1]
REMOTE_SCRIPT = ROOT / "scripts" / "remote_staging_contract.py"
REMOTE_WORKFLOW = ROOT / ".github" / "workflows" / "remote-staging-live-gate.yml"

EXPECTED = "a" * 40
OLD = "b" * 40


def _load_remote_module(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, expected: str = EXPECTED):
    monkeypatch.setenv("REMOTE_STAGING_ARTIFACT_DIR", str(tmp_path / "remote-evidence"))
    monkeypatch.setenv("EXPECTED_GIT_COMMIT", expected)
    spec = importlib.util.spec_from_file_location("remote_staging_contract_v259", REMOTE_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Response:
    status_code = 200
    text = ""

    def __init__(self, release_commit: str):
        self._payload = {
            "status": "ok",
            "environment": "staging",
            "release_commit": release_commit,
        }

    def json(self):
        return dict(self._payload)


class _Client:
    def __init__(self, releases: list[str]):
        self.releases = list(releases)

    def get(self, path: str, timeout: float | None = None):
        assert path == "/api/health"
        assert self.releases
        return _Response(self.releases.pop(0))


@pytest.mark.smoke
def test_v259_health_release_identity_prefers_render_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RENDER_GIT_COMMIT", EXPECTED.upper())
    monkeypatch.setenv("GITHUB_SHA", OLD)
    assert release_commit_from_environment() == EXPECTED


@pytest.mark.smoke
def test_v259_remote_gate_waits_until_expected_release_is_served(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    remote = _load_remote_module(tmp_path, monkeypatch)
    remote.POLL_INTERVAL_SECONDS = 0
    remote.DEPLOY_TIMEOUT_SECONDS = 1

    evidence = remote._wait_for_expected_release(
        _Client([EXPECTED]),
        first_payload={"status": "ok", "environment": "staging", "release_commit": OLD},
    )

    assert evidence["status"] == "matched"
    assert evidence["expected_commit"] == EXPECTED
    assert evidence["served_commit"] == EXPECTED
    assert evidence["attempts"] == 2


def test_v259_remote_gate_rejects_non_full_expected_sha(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    remote = _load_remote_module(tmp_path, monkeypatch, expected="abc1234")
    with pytest.raises(AssertionError, match="40 caracteres"):
        remote._assert_safe_target()


def test_v259_workflow_binds_expected_sha_without_adding_product_routes() -> None:
    workflow = REMOTE_WORKFLOW.read_text(encoding="utf-8")
    remote = REMOTE_SCRIPT.read_text(encoding="utf-8")

    assert "expected_sha:" in workflow
    assert "EXPECTED_GIT_COMMIT: ${{ inputs.expected_sha || github.sha }}" in workflow
    assert 'REMOTE_STAGING_DEPLOY_TIMEOUT_SECONDS: "360"' in workflow
    assert "non-mutating-remote-staging-v3" in remote
    assert "release_commit" in remote
    assert "/api/build" not in remote
