from __future__ import annotations

import os
import secrets
from pathlib import Path

# Vercel Functions run on an ephemeral filesystem. Keep every local write under
# /tmp and never confuse this adapter with the persistent production topology.
INSTANCE_DIR = Path("/tmp/calcula-tu-huella")
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)

_external_database = bool(os.environ.get("DATABASE_URL", "").strip())
_raw_database_url = os.environ.get("DATABASE_URL", "").strip()
if _raw_database_url.startswith("postgresql://"):
    os.environ["DATABASE_URL"] = "postgresql+psycopg://" + _raw_database_url.removeprefix("postgresql://")
elif _raw_database_url.startswith("postgres://"):
    os.environ["DATABASE_URL"] = "postgresql+psycopg://" + _raw_database_url.removeprefix("postgres://")

os.environ.setdefault("APP_ENV", "staging")
os.environ.setdefault("INSTANCE_DIR", str(INSTANCE_DIR))
os.environ.setdefault("SESSION_SECRET", secrets.token_urlsafe(48))
os.environ.setdefault("SESSION_HTTPS_ONLY", "true")
os.environ.setdefault("TRUSTED_HOSTS", "*.vercel.app,localhost,127.0.0.1")
os.environ.setdefault("SEED_DEMO", "true")
os.environ.setdefault("STORAGE_BACKEND", "local")
os.environ.setdefault("EMAIL_BACKEND", "disabled")
os.environ.setdefault("SCHEDULER_ENABLED", "false")
os.environ.setdefault("DEPLOYMENT_STRICT", "false")
os.environ.setdefault("OPEN_BROWSER", "0")
os.environ.setdefault("WEB_CONCURRENCY", "1")
os.environ.setdefault("STRUCTURED_LOGGING", "true")

EXPECTED_EXTERNAL_ALEMBIC_REVISION = "20260812_0040"

if _external_database:
    # External PostgreSQL is never bootstrapped from an import-time serverless
    # request. Schema changes belong to Alembic and must be completed beforehand.
    # This prevents Base.metadata.create_all() from hiding migration drift.
    from sqlalchemy import text
    from app.db.base import ENGINE

    try:
        with ENGINE.connect() as connection:
            revision = connection.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar_one()
    except Exception as exc:  # pragma: no cover - depends on external infrastructure
        raise RuntimeError(
            "La base externa de staging no expone un estado Alembic verificable; "
            "no se iniciará el runtime serverless."
        ) from exc
    if revision != EXPECTED_EXTERNAL_ALEMBIC_REVISION:
        raise RuntimeError(
            "La base externa de staging no está en la revision certificada: "
            f"esperada={EXPECTED_EXTERNAL_ALEMBIC_REVISION}, actual={revision}. "
            "Ejecuta la migración fuera del runtime serverless antes de desplegar."
        )
else:
    # El modo sin DATABASE_URL es explícitamente efímero y sí puede crear su
    # propia SQLite en /tmp para UAT de navegación, CSRF y flujos públicos.
    from app.database import init_db

    init_db()

from app.main import app  # noqa: E402,F401
