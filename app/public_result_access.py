from __future__ import annotations

from datetime import UTC, datetime, timedelta


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def public_result_access_window_label(max_age_hours: int) -> str:
    """Return a human-readable label for the configured public-link window."""
    if max_age_hours > 0 and max_age_hours % 24 == 0:
        days = max_age_hours // 24
        return f"{days} día" if days == 1 else f"{days} días"
    return f"{max_age_hours} hora" if max_age_hours == 1 else f"{max_age_hours} horas"


def public_result_is_expired(
    created_at: datetime | None,
    max_age_hours: int,
    *,
    now: datetime | None = None,
) -> bool:
    """Return whether a public diagnosis result link is no longer accessible.

    This is an access-window policy for the public result URL. It does not
    delete or shorten retention of the underlying commercial lead or diagnosis.
    Missing timestamps and non-positive windows fail closed.
    """
    if created_at is None or max_age_hours <= 0:
        return True

    current = _as_utc(now or datetime.now(UTC))
    created = _as_utc(created_at)
    return current >= created + timedelta(hours=max_age_hours)
