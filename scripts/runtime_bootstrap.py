from __future__ import annotations

import os
import time

from sqlalchemy import select

from app.database import Organization, PlatformSetting, SessionLocal, init_db

INTERNAL_BOOTSTRAP_KEY = "runtime_internal_bootstrap_release"
_TRUE_VALUES = {"1", "true", "yes", "on"}


def _render_staging_release() -> str | None:
    """Return Render's immutable release id only for the staging runtime."""
    if os.getenv("APP_ENV", "production").strip().lower() != "staging":
        return None
    release = os.getenv("RENDER_GIT_COMMIT", "").strip()
    return release or None


def _force_bootstrap() -> bool:
    return os.getenv("FORCE_RUNTIME_BOOTSTRAP", "").strip().lower() in _TRUE_VALUES


def _first_organization_id(session) -> int | None:
    return session.scalar(select(Organization.id).order_by(Organization.id.asc()).limit(1))


def _read_release_marker() -> str | None:
    with SessionLocal() as session:
        organization_id = _first_organization_id(session)
        if organization_id is None:
            return None
        row = session.scalar(
            select(PlatformSetting).where(
                PlatformSetting.organization_id == organization_id,
                PlatformSetting.key == INTERNAL_BOOTSTRAP_KEY,
            )
        )
        return row.value.strip() if row and row.value else None


def _write_release_marker(release: str) -> None:
    with SessionLocal() as session:
        organization_id = _first_organization_id(session)
        if organization_id is None:
            # An empty/no-bootstrap database is safer to reconcile again than to
            # fabricate an organization only for a technical marker.
            return
        row = session.scalar(
            select(PlatformSetting).where(
                PlatformSetting.organization_id == organization_id,
                PlatformSetting.key == INTERNAL_BOOTSTRAP_KEY,
            )
        )
        if row is None:
            row = PlatformSetting(
                organization_id=organization_id,
                key=INTERNAL_BOOTSTRAP_KEY,
                value_type="internal",
                description="Marcador técnico del bootstrap por release de Render.",
                updated_by="runtime",
            )
            session.add(row)
        row.value = release
        row.value_type = "internal"
        row.description = "Marcador técnico del bootstrap por release de Render."
        row.updated_by = "runtime"
        session.commit()


def run_runtime_bootstrap() -> dict[str, object]:
    """Reconcile defaults once per Render staging release, never skipping Alembic."""
    release = _render_staging_release()
    forced = _force_bootstrap()
    started = time.monotonic()

    if release and not forced and _read_release_marker() == release:
        elapsed = time.monotonic() - started
        print(
            "Bootstrap runtime ya verificado para este release; "
            f"reconciliación omitida ({elapsed:.2f}s)."
        )
        return {"mode": "cached", "release": release, "elapsed_seconds": elapsed}

    init_db()
    if release:
        _write_release_marker(release)

    elapsed = time.monotonic() - started
    mode = "forced" if forced else "full"
    print(f"Esquema e inicialización verificados ({mode}, {elapsed:.2f}s).")
    return {"mode": mode, "release": release, "elapsed_seconds": elapsed}


if __name__ == "__main__":
    run_runtime_bootstrap()
