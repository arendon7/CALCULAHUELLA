from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from ..config import settings
from ..database import Inventory, InventoryFacility, add_audit
from ..repositories.organizations import list_facilities_by_ids


def create_inventory(
    session: Session,
    organization_id: int,
    *,
    actor_email: str,
    name: str,
    start_date: date,
    end_date: date,
    objective: str,
    base_year: int,
    methodology: str,
    methodology_version: str,
    gwp_version: str,
    consolidation_approach: str,
    materiality_threshold: float,
    notes: str,
    facility_ids: list[int],
) -> Inventory:
    inventory = Inventory(
        organization_id=organization_id,
        name=name.strip(),
        start_date=start_date,
        end_date=end_date,
        objective=objective.strip(),
        base_year=base_year,
        methodology=methodology.strip(),
        methodology_version=methodology_version.strip(),
        gwp_version=gwp_version.strip(),
        consolidation_approach=consolidation_approach.strip(),
        materiality_threshold=max(materiality_threshold, 0),
        notes=notes.strip(),
        status="Borrador",
        progress=14,
        current_stage="Configuración",
        version=".".join(settings.version.split(".")[:2]),
    )
    session.add(inventory)
    session.flush()
    for facility in list_facilities_by_ids(session, organization_id, facility_ids):
        session.add(
            InventoryFacility(
                inventory_id=inventory.id,
                facility_id=facility.id,
                included=True,
                inclusion_percentage=100,
            )
        )
    add_audit(
        session,
        organization_id,
        actor_email,
        "CREAR",
        "Inventario",
        inventory.name,
        f"Periodo {inventory.start_date} a {inventory.end_date}",
    )
    return inventory
