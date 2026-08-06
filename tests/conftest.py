from __future__ import annotations

import atexit
import os
import shutil
import tempfile
from pathlib import Path

import pytest

# Configure an isolated runtime before any test module imports app.config/database.
_TEST_INSTANCE = Path(tempfile.mkdtemp(prefix="cth_pytest_"))
_TEST_DATABASE = _TEST_INSTANCE / "calculatuhuella.db"
_SEED_DATABASE = _TEST_INSTANCE / "calculatuhuella.seed.db"
os.environ["INSTANCE_DIR"] = str(_TEST_INSTANCE)
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DATABASE}"
os.environ["APP_ENV"] = "local"
os.environ["SEED_DEMO"] = "1"
os.environ["SCHEDULER_ENABLED"] = "0"
os.environ["STRUCTURED_LOGGING"] = "0"
os.environ["PBKDF2_ITERATIONS"] = "10000"
os.environ["CSRF_ENABLED"] = "1"

_TRANSIENT_DIRS = (
    "backups",
    "certifications",
    "import_staging",
    "logs",
    "outbox",
    "reports",
    "uploads",
)


def _cleanup() -> None:
    shutil.rmtree(_TEST_INSTANCE, ignore_errors=True)


atexit.register(_cleanup)


@pytest.fixture(scope="session", autouse=True)
def _seeded_database_snapshot() -> Path:
    """Create the full demo database once for the complete test session."""
    from app.database import Base, ENGINE, init_db

    Base.metadata.drop_all(ENGINE)
    init_db()
    ENGINE.dispose()
    shutil.copy2(_TEST_DATABASE, _SEED_DATABASE)
    return _SEED_DATABASE


def restore_seed_database() -> None:
    """Restore the test seed on demand for tests that need an internal reset."""
    from app.database import ENGINE

    if not _SEED_DATABASE.exists():
        raise RuntimeError("La base semilla de pruebas aún no está disponible.")
    ENGINE.dispose()
    shutil.copy2(_SEED_DATABASE, _TEST_DATABASE)


@pytest.fixture(autouse=True)
def isolated_seeded_database(_seeded_database_snapshot: Path):
    """Restore a byte-identical SQLite seed before every test.

    This replaces dozens of repeated 120-table rebuilds while giving each test
    stronger isolation than the previous module-scoped reset pattern.
    """
    from app.database import ENGINE

    restore_seed_database()
    for name in _TRANSIENT_DIRS:
        path = _TEST_INSTANCE / name
        shutil.rmtree(path, ignore_errors=True)
        path.mkdir(parents=True, exist_ok=True)
    (_TEST_INSTANCE / "certifications" / "demo").mkdir(parents=True, exist_ok=True)
    (_TEST_INSTANCE / "mail_outbox").mkdir(parents=True, exist_ok=True)
    yield
    ENGINE.dispose()
