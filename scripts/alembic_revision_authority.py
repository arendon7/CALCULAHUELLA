from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

ROOT = Path(__file__).resolve().parents[1]


class MigrationHeadAuthorityError(AssertionError):
    """Raised when the repository migration graph has no unique Alembic head."""


def repository_head_revisions(root: Path = ROOT) -> tuple[str, ...]:
    """Return the Alembic heads declared by the repository migration graph."""
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str((root / "migrations").resolve()))
    return tuple(ScriptDirectory.from_config(config).get_heads())


def repository_head_revision(root: Path = ROOT) -> str:
    """Return the single authoritative Alembic head, failing closed on graph drift."""
    heads = repository_head_revisions(root)
    if len(heads) != 1:
        rendered = ", ".join(heads) if heads else "ninguno"
        raise MigrationHeadAuthorityError(
            "Se esperaba un único head Alembic del repositorio; "
            f"encontrados {len(heads)}: {rendered}"
        )
    return heads[0]
