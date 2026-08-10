from __future__ import annotations

from pathlib import Path

from sqlalchemy import func, select

from app.database import Base, ENGINE, Organization, SessionLocal, init_db

ROOT = Path(__file__).resolve().parents[1]


def test_v160_d2a_database_keeps_init_db_as_compatibility_facade():
    database = (ROOT / "app/database.py").read_text(encoding="utf-8")
    seed = (ROOT / "app/seed.py").read_text(encoding="utf-8")
    assert "from .seed import init_db as bootstrap_init_db" in database
    assert "Industrias Andinas Demo S.A.S." not in database
    assert "def init_db() -> None:" in seed
    assert "Industrias Andinas Demo S.A.S." in seed
    assert len(database.splitlines()) < 1750


def test_v160_d2a_bootstrap_remains_idempotent_on_seeded_database():
    with SessionLocal() as session:
        before = session.scalar(select(func.count()).select_from(Organization))
    init_db()
    with SessionLocal() as session:
        after = session.scalar(select(func.count()).select_from(Organization))
    assert after == before
    assert len(Base.metadata.tables) == 124
    assert ENGINE is not None
