from __future__ import annotations

from pathlib import Path

from app.database import AppUser, hash_password


ROOT = Path(__file__).resolve().parents[1]
LEGACY_CHECKPOINT = ROOT / "migrations" / "versions" / "20260806_0038_legacy_schema_compat.py"
MIGRATION = ROOT / "migrations" / "versions" / "20260810_0038_expand_app_user_password_hash.py"


def test_v200_password_hash_column_fits_current_pbkdf2_encoding() -> None:
    encoded = hash_password("V2-readiness-password")
    capacity = AppUser.__table__.c.password_hash.type.length
    assert encoded.startswith("pbkdf2_sha256$")
    assert capacity is not None
    assert len(encoded) <= capacity
    assert capacity >= 255


def test_v200_password_hash_capacity_is_managed_by_compatible_alembic_lineage() -> None:
    checkpoint = LEGACY_CHECKPOINT.read_text(encoding="utf-8")
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'revision = "20260806_0038"' in checkpoint
    assert 'down_revision = "20260806_0037"' in checkpoint
    assert '_ensure_min_length("app_users", "password_hash", 255)' in checkpoint

    assert 'revision = "20260810_0038"' in source
    assert 'down_revision = "20260806_0038"' in source
    assert 'op.batch_alter_table("app_users")' in source
    assert '"password_hash"' in source
    assert "sa.String(length=255)" in source
    assert "current_length >= 255" in source


def test_v200_password_migrations_never_force_a_capacity_reduction_on_upgrade() -> None:
    checkpoint = LEGACY_CHECKPOINT.read_text(encoding="utf-8")
    source = MIGRATION.read_text(encoding="utf-8")
    upgrade_checkpoint = checkpoint.split("def upgrade()", 1)[1].split("def downgrade()", 1)[0]
    upgrade_source = source.split("def upgrade()", 1)[1].split("def downgrade()", 1)[0]
    assert "length=64" not in upgrade_checkpoint
    assert "length=64" not in upgrade_source
