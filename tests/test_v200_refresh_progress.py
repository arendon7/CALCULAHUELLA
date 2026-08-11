from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import ActivityData, EmissionSource, Inventory, SessionLocal, refresh_progress


def _activity(source_id: int, month: int) -> ActivityData:
    return ActivityData(
        source_id=source_id,
        period_start=date(2025, month, 1),
        period_end=date(2025, month, 28),
        value=20.0,
        unit="t",
        data_origin="Registro operativo",
        quality_level="B",
        status="Cargado",
        created_by="test@calculatuhuella.local",
    )


def test_refresh_progress_reads_flushed_rows_instead_of_stale_relationship() -> None:
    with SessionLocal() as session:
        inventory = session.scalar(
            select(Inventory)
            .where(Inventory.name == "Inventario corporativo 2025")
            .options(selectinload(Inventory.sources).selectinload(EmissionSource.activity_records))
        )
        assert inventory is not None
        residuos = next(source for source in inventory.sources if source.name == "Residuos")

        # La semilla trae enero-junio. Dejamos la relación cargada deliberadamente en 11 meses.
        for month in range(7, 12):
            session.add(_activity(residuos.id, month))
        session.flush()
        session.expire(residuos, ["activity_records"])
        assert len(residuos.activity_records) == 11

        # Diciembre se inserta por FK, como lo hace Captura guiada. La colección sigue obsoleta.
        session.add(_activity(residuos.id, 12))
        session.flush()
        assert len(residuos.activity_records) == 11

        refresh_progress(session, inventory)

        assert residuos.progress == 100
        assert residuos.status == "Completado"


def test_refresh_progress_preserves_supplier_managed_progress_authority() -> None:
    with SessionLocal() as session:
        inventory = session.scalar(
            select(Inventory)
            .where(Inventory.name == "Inventario corporativo 2025")
            .options(selectinload(Inventory.sources))
        )
        assert inventory is not None
        supplier_source = next(
            source for source in inventory.sources if source.category == "Datos específicos de proveedores"
        )
        supplier_source.progress = 73
        supplier_source.status = "En progreso"
        session.flush()

        refresh_progress(session, inventory)

        assert supplier_source.progress == 73
        assert supplier_source.status == "En progreso"
