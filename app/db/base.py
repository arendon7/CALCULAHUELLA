from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from ..config import INSTANCE_DIR, settings

UPLOAD_DIR = INSTANCE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path(settings.database_url.removeprefix("sqlite:///")) if settings.database_url.startswith("sqlite:///") else None
_engine_options: dict[str, object] = {"pool_pre_ping": True}
if settings.database_url.startswith("sqlite"):
    _engine_options["connect_args"] = {"check_same_thread": False}
ENGINE = create_engine(settings.database_url, **_engine_options)
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass
