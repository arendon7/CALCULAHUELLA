from __future__ import annotations

from pathlib import Path

from app.database import AppUser, hash_password


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "migrations" / "versions" / "20260810_0038_expand_app_user_password_hash.py"


def test_v200_password_hash_column_fits_current_pbkdf2_encoding() -> None:
    encoded = hash_password("V2-readiness-password")
    capacity = AppUser.__table__.c.password_hash.type.length
    assert encoded.startswith("pbkdf2_sha256$")
    assert capacity is not None
    assert len(encoded) <= capacity
    assert capacity >= 255


def test_v200_password_hash_capacity_is_managed_by_alembic() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    assert 'revision = "20260810_0038"' in source
    assert 'down_revision = "20260806_0037"' in source
    assert 'op.batch_alter_table("app_users")' in source
    assert '"password_hash"' in source
    assert "sa.String(length=64)" in source
    assert "sa.String(length=255)" in source
