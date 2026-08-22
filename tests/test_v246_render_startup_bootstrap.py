from __future__ import annotations

from pathlib import Path

from sqlalchemy import delete, select

from app.database import Organization, PlatformSetting, SessionLocal
from scripts import runtime_bootstrap

ROOT = Path(__file__).resolve().parents[1]


def _clear_marker() -> None:
    with SessionLocal() as session:
        session.execute(
            delete(PlatformSetting).where(
                PlatformSetting.key == runtime_bootstrap.INTERNAL_BOOTSTRAP_KEY
            )
        )
        session.commit()


def _marker_value() -> str | None:
    with SessionLocal() as session:
        return session.scalar(
            select(PlatformSetting.value).where(
                PlatformSetting.key == runtime_bootstrap.INTERNAL_BOOTSTRAP_KEY
            )
        )


def test_v246_startup_keeps_alembic_fail_closed_before_cached_bootstrap() -> None:
    text = (ROOT / "start_prod.sh").read_text(encoding="utf-8")
    migration = text.index('"$PY" -m alembic upgrade head')
    bootstrap = text.index('"$PY" -m scripts.runtime_bootstrap')
    server = text.index('exec "$PY" -m uvicorn app.main:app')

    assert migration < bootstrap < server
    assert '"$PY" scripts/runtime_bootstrap.py' not in text
    assert "check_ready.py" in text
    assert "FORCE_RUNTIME_BOOTSTRAP" not in text  # override is consumed only by the Python runtime helper


def test_v246_release_cache_is_only_enabled_for_render_staging(monkeypatch) -> None:
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abc123")
    monkeypatch.setenv("APP_ENV", "production")
    assert runtime_bootstrap._render_staging_release() is None

    monkeypatch.setenv("APP_ENV", "staging")
    assert runtime_bootstrap._render_staging_release() == "abc123"

    monkeypatch.delenv("RENDER_GIT_COMMIT")
    assert runtime_bootstrap._render_staging_release() is None


def test_v246_same_release_skips_reconciliation(monkeypatch) -> None:
    _clear_marker()
    with SessionLocal() as session:
        organization_id = session.scalar(select(Organization.id).order_by(Organization.id).limit(1))
        assert organization_id is not None
        session.add(
            PlatformSetting(
                organization_id=organization_id,
                key=runtime_bootstrap.INTERNAL_BOOTSTRAP_KEY,
                value="same-release",
                value_type="internal",
            )
        )
        session.commit()

    calls: list[str] = []
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("RENDER_GIT_COMMIT", "same-release")
    monkeypatch.delenv("FORCE_RUNTIME_BOOTSTRAP", raising=False)
    monkeypatch.setattr(runtime_bootstrap, "init_db", lambda: calls.append("init"))

    result = runtime_bootstrap.run_runtime_bootstrap()

    assert result["mode"] == "cached"
    assert calls == []


def test_v246_changed_release_reconciles_once_and_persists_marker(monkeypatch) -> None:
    _clear_marker()
    calls: list[str] = []
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("RENDER_GIT_COMMIT", "release-next")
    monkeypatch.delenv("FORCE_RUNTIME_BOOTSTRAP", raising=False)
    monkeypatch.setattr(runtime_bootstrap, "init_db", lambda: calls.append("init"))

    first = runtime_bootstrap.run_runtime_bootstrap()
    second = runtime_bootstrap.run_runtime_bootstrap()

    assert first["mode"] == "full"
    assert second["mode"] == "cached"
    assert calls == ["init"]
    assert _marker_value() == "release-next"


def test_v246_force_override_reconciles_even_when_release_matches(monkeypatch) -> None:
    _clear_marker()
    calls: list[str] = []
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("RENDER_GIT_COMMIT", "forced-release")
    monkeypatch.setenv("FORCE_RUNTIME_BOOTSTRAP", "1")
    monkeypatch.setattr(runtime_bootstrap, "init_db", lambda: calls.append("init"))

    first = runtime_bootstrap.run_runtime_bootstrap()
    second = runtime_bootstrap.run_runtime_bootstrap()

    assert first["mode"] == "forced"
    assert second["mode"] == "forced"
    assert calls == ["init", "init"]
    assert _marker_value() == "forced-release"


def test_v246_internal_runtime_setting_is_hidden_and_reserved() -> None:
    text = (ROOT / "app" / "platform_admin_web.py").read_text(encoding="utf-8")

    assert 'INTERNAL_PLATFORM_SETTING_PREFIX = "runtime_internal_"' in text
    assert "if not row.key.startswith(INTERNAL_PLATFORM_SETTING_PREFIX)" in text
    assert "if clean_key.startswith(INTERNAL_PLATFORM_SETTING_PREFIX):" in text
    assert 'raise HTTPException(400, "Clave reservada para el runtime")' in text
