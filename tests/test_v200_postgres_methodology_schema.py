from __future__ import annotations

from pathlib import Path

from app.database import MethodologySourceDocument


ROOT = Path(__file__).resolve().parents[1]
SECTOR_LIBRARY = ROOT / "app" / "sector_library.py"
LEGACY_CHECKPOINT = ROOT / "migrations" / "versions" / "20260806_0038_legacy_schema_compat.py"
MIGRATION = ROOT / "migrations" / "versions" / "20260810_0039_expand_methodology_source_status.py"


def test_v200_methodology_source_status_fits_canonical_seed_values() -> None:
    source = SECTOR_LIBRARY.read_text(encoding="utf-8")
    canonical_status = "Fuente oficial identificada · transcripción controlada pendiente"
    capacity = MethodologySourceDocument.__table__.c.status.type.length
    assert canonical_status in source
    assert capacity is not None
    assert len(canonical_status) <= capacity
    assert capacity >= 160


def test_v200_methodology_source_status_capacity_is_managed_by_compatible_alembic_lineage() -> None:
    checkpoint = LEGACY_CHECKPOINT.read_text(encoding="utf-8")
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'revision = "20260806_0038"' in checkpoint
    assert '_ensure_min_length("methodology_source_documents", "status", 160)' in checkpoint

    assert 'revision = "20260810_0039"' in source
    assert 'down_revision = "20260810_0038"' in source
    assert 'op.batch_alter_table("methodology_source_documents")' in source
    assert '"status"' in source
    assert "sa.String(length=160)" in source
    assert "current_length >= 160" in source


def test_v200_methodology_status_upgrade_never_shrinks_live_capacity() -> None:
    checkpoint = LEGACY_CHECKPOINT.read_text(encoding="utf-8")
    source = MIGRATION.read_text(encoding="utf-8")
    upgrade_checkpoint = checkpoint.split("def upgrade()", 1)[1].split("def downgrade()", 1)[0]
    upgrade_source = source.split("def upgrade()", 1)[1].split("def downgrade()", 1)[0]
    assert "length=40" not in upgrade_checkpoint
    assert "length=100" not in upgrade_checkpoint
    assert "length=40" not in upgrade_source
    assert "length=100" not in upgrade_source
