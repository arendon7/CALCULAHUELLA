from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import EmissionSource, Inventory, SessionLocal, refresh_inventory_progress
from app.pilot_execution import start_pilot_execution


def test_generic_progress_refresh_does_not_own_semantic_pilot_stage() -> None:
    with SessionLocal() as session:
        inventory = session.scalar(
            select(Inventory)
            .where(Inventory.name == "Inventario corporativo 2025")
            .options(selectinload(Inventory.sources))
        )
        assert inventory is not None
        inventory.status = "Borrador"
        inventory.locked = False
        inventory.current_stage = "Preparación del piloto"
        for source in inventory.sources:
            source.progress = 100
        session.flush()

        refresh_inventory_progress(session, inventory)

        assert inventory.progress == 100
        assert inventory.current_stage == "Preparación del piloto"


def test_pilot_lifecycle_explicitly_advances_to_collection_after_setup() -> None:
    with SessionLocal() as session:
        execution = start_pilot_execution(
            session,
            organization_id=1,
            user_email="consultor@test",
            user_name="Consultor prueba",
        )
        session.flush()
        inventory = session.get(Inventory, execution.inventory_id)
        assert inventory is not None
        assert inventory.status == "Borrador"
        assert inventory.current_stage == "Recolección"
        assert session.scalar(
            select(EmissionSource.id).where(EmissionSource.inventory_id == inventory.id).limit(1)
        ) is not None
