from __future__ import annotations

from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from scripts import alembic_revision_authority as authority

ROOT = Path(__file__).resolve().parents[1]
POSTGRES_GATE = ROOT / "scripts" / "postgres_legacy_migration_gate.py"
LEGACY_COMPAT = ROOT / "tests" / "test_migration_legacy_compat.py"
SERVERLESS_WORKFLOW = ROOT / ".github" / "workflows" / "vercel-staging-contract.yml"


class _FakeScriptDirectory:
    def __init__(self, heads: tuple[str, ...]):
        self._heads = heads

    def get_heads(self) -> tuple[str, ...]:
        return self._heads


class _FakeScriptDirectoryFactory:
    heads: tuple[str, ...] = ()

    @staticmethod
    def from_config(_config: Config) -> _FakeScriptDirectory:
        return _FakeScriptDirectory(_FakeScriptDirectoryFactory.heads)


def test_v2621_repository_head_authority_matches_alembic_graph() -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str((ROOT / "migrations").resolve()))
    heads = tuple(ScriptDirectory.from_config(config).get_heads())

    assert len(heads) == 1
    assert authority.repository_head_revision(ROOT) == heads[0]


def test_v2621_repository_head_authority_fails_closed_on_multiple_heads(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeScriptDirectoryFactory.heads = ("head_a", "head_b")
    monkeypatch.setattr(authority, "ScriptDirectory", _FakeScriptDirectoryFactory)

    with pytest.raises(authority.MigrationHeadAuthorityError, match="único head Alembic"):
        authority.repository_head_revision(ROOT)


def test_v2621_repository_head_authority_fails_closed_without_head(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeScriptDirectoryFactory.heads = ()
    monkeypatch.setattr(authority, "ScriptDirectory", _FakeScriptDirectoryFactory)

    with pytest.raises(authority.MigrationHeadAuthorityError, match="ninguno"):
        authority.repository_head_revision(ROOT)


def test_v2621_postgres_gate_uses_repository_authority_without_current_head_constant() -> None:
    source = POSTGRES_GATE.read_text(encoding="utf-8")

    assert "from scripts.alembic_revision_authority import repository_head_revision" in source
    assert "expected_head_revision = repository_head_revision(ROOT)" in source
    assert "revision != expected_head_revision" in source
    assert '"repository_head_revision": expected_head_revision' in source
    assert "HEAD_REVISION =" not in source


def test_v2621_legacy_compat_test_no_longer_duplicates_current_head_authority() -> None:
    source = LEGACY_COMPAT.read_text(encoding="utf-8")

    assert "from scripts.alembic_revision_authority import repository_head_revision" in source
    assert "HEAD_REVISION =" not in source
    assert "repository_head_revision(ROOT)" in source


def test_v2621_serverless_workflow_executes_and_tracks_authority_contract() -> None:
    source = SERVERLESS_WORKFLOW.read_text(encoding="utf-8")

    contract = "tests/test_v2621_serverless_migration_head_authority.py"
    assert f'- "{contract}"' in source
    assert f"pytest -q {contract}" in source
    assert 'run: python -m scripts.postgres_legacy_migration_gate' in source
