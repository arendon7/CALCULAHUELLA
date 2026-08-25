from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.public_result_access import public_result_is_expired


ROOT = Path(__file__).resolve().parents[1]


def test_v257_public_result_expiry_boundary_is_exact() -> None:
    created = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)

    assert not public_result_is_expired(
        created,
        720,
        now=created + timedelta(hours=719, minutes=59, seconds=59),
    )
    assert public_result_is_expired(
        created,
        720,
        now=created + timedelta(hours=720),
    )


def test_v257_naive_database_timestamps_are_interpreted_as_utc() -> None:
    created = datetime(2026, 8, 1, 12, 0)
    now = datetime(2026, 8, 2, 12, 0, tzinfo=UTC)

    assert not public_result_is_expired(created, 720, now=now)


def test_v257_invalid_or_missing_timestamp_fails_closed() -> None:
    now = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)

    assert public_result_is_expired(None, 720, now=now)
    assert public_result_is_expired(now, 0, now=now)
    assert public_result_is_expired(now, -1, now=now)


def test_v257_public_link_policy_is_explicit_and_configurable() -> None:
    config = (ROOT / "app" / "config.py").read_text(encoding="utf-8")
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    render = (ROOT / "render.yaml").read_text(encoding="utf-8")

    assert 'PUBLIC_RESULT_MAX_AGE_HOURS", "720"' in config
    assert "PUBLIC_RESULT_MAX_AGE_HOURS=720" in env_example
    assert "- key: PUBLIC_RESULT_MAX_AGE_HOURS\n        value: \"720\"" in render


def test_v257_expired_result_uses_same_not_found_contract_without_deleting_data() -> None:
    source = (ROOT / "app" / "product_intelligence_web.py").read_text(encoding="utf-8")

    assert "public_result_is_expired" in source
    assert "settings.public_result_max_age_hours" in source
    assert 'raise HTTPException(404, "Diagnóstico no encontrado")' in source
    assert "session.delete(lead)" not in source
