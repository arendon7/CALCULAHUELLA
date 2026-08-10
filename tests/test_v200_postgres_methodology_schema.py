from __future__ import annotations

from pathlib import Path

from app.database import MethodologySourceDocument


ROOT = Path(__file__).resolve().parents[1]
SECTOR_LIBRARY = ROOT / "app" / "sector_library.py"
MIGRATION = ROOT / "migrations" / "versions" / "20260810_0039_expand_methodology_source_status.py"


def test_v200_methodology_source_status_fits_canonical_seed_values() -> None:
    source = SECTOR_LIBRARY.read_text(encoding="utf-8")
    canonical_status = "Fuente oficial identificada · transcripción controlada pendiente"
    capacity = MethodologySourceDocument.__table__.c.status.type.length
    assert canonical_status in source
    assert capacity is not None
    assert len(canonical_status) <= capacity
    assert capacity >= 100


def test_v200_methodology_source_status_capacity_is_managed_by_alembic() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    assert 'revision = "20260810_0039"' in source
    assert 'down_revision = "20260810_0038"' in source
    assert 'op.batch_alter_table("methodology_source_documents")' in source
    assert '"status"' in source
    assert "sa.String(length=40)" in source
    assert "sa.String(length=100)" in source
