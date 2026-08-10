from __future__ import annotations

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .database import add_audit, get_db, refresh_progress
from .db.models import (
    EmissionFactor,
    EmissionFactorVersion,
    EmissionSource,
    SectorTemplate,
    SourceFactorAssignment,
)


def register_sectorization_routes(
    app,
    templates,
    common_context,
    require_user,
    ensure_capability,
    set_flash,
    get_inventory,
    ensure_inventory_editable,
) -> None:
    @app.get("/sectorizacion", response_class=HTMLResponse)
    def sectorization_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        inventory = get_inventory(session, user)
        templates_list = list(session.scalars(select(SectorTemplate).where(SectorTemplate.active.is_(True)).options(selectinload(SectorTemplate.source_items)).order_by(SectorTemplate.sector)))
        selected_template = next((item for item in templates_list if item.sector == inventory.organization.sector), None)
        return templates.TemplateResponse(request=request, name="sectorization.html", context=common_context(request, session, user, "sectorization", inventory=inventory, templates_list=templates_list, selected_template=selected_template, facilities=[link.facility for link in inventory.facility_links if link.included]))

    @app.post("/sectorizacion/aplicar")
    def apply_sector_template(request: Request, inventory_id: int = Form(...), template_id: int = Form(...), facility_id: int | None = Form(None), include_optional: bool = Form(False), session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_sources")
        inventory = get_inventory(session, user, inventory_id)
        ensure_inventory_editable(inventory)
        template = session.scalar(select(SectorTemplate).where(SectorTemplate.id == template_id, SectorTemplate.active.is_(True)).options(selectinload(SectorTemplate.source_items)))
        if not template:
            raise HTTPException(404, "Plantilla sectorial no encontrada")
        allowed_facilities = {link.facility_id for link in inventory.facility_links if link.included}
        selected_facility_id = facility_id if facility_id in allowed_facilities else (next(iter(allowed_facilities)) if allowed_facilities else None)
        existing_keys = {(source.name.strip().lower(), source.category.strip().lower()) for source in inventory.sources}
        created = 0
        assigned = 0
        for item in template.source_items:
            if not item.recommended and not include_optional:
                continue
            key = (item.name.strip().lower(), item.category.strip().lower())
            if key in existing_keys:
                continue
            source = EmissionSource(inventory_id=inventory.id, facility_id=selected_facility_id, name=item.name, scope=item.scope, category=item.category, responsible=item.responsible, materiality=item.materiality, data_frequency=item.data_frequency, preferred_unit=item.preferred_unit, icon=item.icon, included=True, status="Pendiente", progress=0)
            session.add(source)
            session.flush()
            existing_keys.add(key)
            created += 1
            if item.factor_activity_type:
                factor_versions = list(session.scalars(select(EmissionFactorVersion).join(EmissionFactor).where(EmissionFactor.activity_type == item.factor_activity_type, EmissionFactorVersion.status == "Aprobado")))
                for version in factor_versions:
                    session.add(SourceFactorAssignment(source_id=source.id, factor_version_id=version.id, active=True, assigned_by=str(user["email"]), notes=f"Asignación automática desde {template.name}"))
                    assigned += 1
        refresh_progress(session, inventory)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "APLICAR", "Plantilla sectorial", template.name, f"{created} fuentes creadas; {assigned} factores asignados")
        session.commit()
        set_flash(request, f"Plantilla aplicada: {created} fuentes nuevas y {assigned} asignaciones de factor.")
        return RedirectResponse("/sectorizacion", status_code=303)
