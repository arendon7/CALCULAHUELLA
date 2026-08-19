from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v247_render_blueprint_binds_dedicated_managed_database_url() -> None:
    text = (ROOT / "render.yaml").read_text(encoding="utf-8")

    dedicated = """- key: RENDER_DATABASE_URL\n        fromDatabase:\n          name: calcula-tu-huella-preview-db\n          property: connectionString"""
    compatibility = """- key: DATABASE_URL\n        fromDatabase:\n          name: calcula-tu-huella-preview-db\n          property: connectionString"""

    assert dedicated in text
    assert compatibility in text
    assert "RENDER_PREVIEW_DB_ONLY" in text


def test_v247_startup_prefers_dedicated_render_database_before_drift_guard() -> None:
    text = (ROOT / "start_prod.sh").read_text(encoding="utf-8")

    dedicated_binding = 'export DATABASE_URL="$RENDER_DATABASE_URL"'
    drift_guard = '"${DATABASE_URL:-}" == *"supabase.com"*'
    migration = '"$PY" -m alembic upgrade head'

    assert dedicated_binding in text
    assert drift_guard in text
    assert text.index(dedicated_binding) < text.index(drift_guard) < text.index(migration)
