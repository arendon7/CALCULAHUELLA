from __future__ import annotations

import os
import secrets
from pathlib import Path

# Vercel Functions run on an ephemeral filesystem. Keep every local write under
# /tmp and never confuse this adapter with the persistent production topology.
INSTANCE_DIR = Path("/tmp/calcula-tu-huella")
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)

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

# If DATABASE_URL is injected by the hosting environment, the application uses
# PostgreSQL. Without it, this preview falls back to an ephemeral SQLite demo so
# the public UX can still be exercised without pretending data persistence.
from app.database import init_db

init_db()

from app.main import app  # noqa: E402,F401
