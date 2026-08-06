from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import LandCarbonEntry, add_audit, get_db
from .land_removals import CARBON_POOLS, ENTRY_TYPES, LAND_CATEGORIES, SCOPES, TRACEABILITY_LEVELS, land_summary, validate_entry


def register_land_removals_routes(app, templates, common_context, require_user, ensure_capability, set_flash, get_inventory, ensure_inventory_editable):
    @app.get("/metodologia/tierras-remociones", response_class=HTMLResponse)
    def page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "view_methodology")
        inventory = get_inventory(session, user)
        entries = list(session.scalars(select(LandCarbonEntry).where(LandCarbonEntry.inventory_id == inventory.id).order_by(LandCarbonEntry.created_at.desc())))
        return templates.TemplateResponse(request=request, name="land_removals.html", context=common_context(
            request, session, user, "land_removals", inventory=inventory, entries=entries, summary=land_summary(entries),
            entry_types=ENTRY_TYPES, land_categories=LAND_CATEGORIES, carbon_pools=CARBON_POOLS, scopes=SCOPES, traceability_levels=TRACEABILITY_LEVELS,
        ))

    @app.post("/metodologia/tierras-remociones/nueva")
    def create(
        request: Request, entry_type: str = Form(...), activity_name: str = Form(...), land_category: str = Form("No aplica"),
        carbon_pool: str = Form("No aplica"), location: str = Form(""), reporting_scope: str = Form("Fuera de alcances"),
        gas: str = Form("CO2"), quantity_tco2e: float = Form(...), start_date: date = Form(...), end_date: date = Form(...),
        methodology: str = Form(...), source_reference: str = Form(...), traceability_level: str = Form("País de origen"),
        uncertainty_percentage: float = Form(0), storage_duration_years: int = Form(0), reversal_monitoring: str | None = Form(None),
        additionality_claimed: str | None = Form(None), lifecycle_complete: str | None = Form(None), verified: str | None = Form(None),
        notes: str = Form(""), session: Session = Depends(get_db), user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_methodology_governance")
        inventory = get_inventory(session, user); ensure_inventory_editable(inventory)
        payload = locals().copy()
        payload.update({"reversal_monitoring": reversal_monitoring is not None, "additionality_claimed": additionality_claimed is not None, "lifecycle_complete": lifecycle_complete is not None, "verified": verified is not None})
        errors = validate_entry(payload)
        if errors:
            set_flash(request, " ".join(errors), "error")
            return RedirectResponse("/metodologia/tierras-remociones#nueva", status_code=303)
        item = LandCarbonEntry(
            inventory_id=inventory.id, entry_type=entry_type, activity_name=activity_name.strip(), land_category=land_category, carbon_pool=carbon_pool,
            location=location.strip(), reporting_scope=reporting_scope, gas=gas.upper(), quantity_tco2e=quantity_tco2e, start_date=start_date, end_date=end_date,
            methodology=methodology.strip(), source_reference=source_reference.strip(), traceability_level=traceability_level, uncertainty_percentage=uncertainty_percentage,
            storage_duration_years=max(storage_duration_years, 0), reversal_monitoring=reversal_monitoring is not None, additionality_claimed=additionality_claimed is not None,
            lifecycle_complete=lifecycle_complete is not None, verified=verified is not None, notes=notes.strip(), created_by=str(user["email"]),
        )
        session.add(item); session.flush()
        add_audit(session, int(user["organization_id"]), str(user["email"]), "CREAR", "Partida de tierras y remociones", item.activity_name, new_value=f"{entry_type} · {quantity_tco2e:.6f} tCO2e")
        session.commit(); set_flash(request, "Partida registrada sin netear automáticamente el inventario.")
        return RedirectResponse("/metodologia/tierras-remociones", status_code=303)

    @app.post("/metodologia/tierras-remociones/{item_id}/revisar")
    def review(item_id: int, request: Request, status: str = Form(...), session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "review")
        inventory = get_inventory(session, user)
        item = session.scalar(select(LandCarbonEntry).where(LandCarbonEntry.id == item_id, LandCarbonEntry.inventory_id == inventory.id))
        if not item: raise HTTPException(404, "Partida no encontrada")
        if status not in {"Borrador", "En revisión", "Aprobado", "Rechazado"}: raise HTTPException(400, "Estado inválido")
        previous=item.status; item.status=status; item.reviewed_by=str(user["email"]); item.reviewed_at=datetime.now(UTC)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "REVISAR", "Partida de tierras y remociones", item.activity_name, previous_value=previous, new_value=status)
        session.commit(); set_flash(request, "Revisión registrada.")
        return RedirectResponse("/metodologia/tierras-remociones", status_code=303)

    @app.get("/api/metodologia/tierras-remociones")
    def api(session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "view_methodology")
        inventory=get_inventory(session,user); entries=list(session.scalars(select(LandCarbonEntry).where(LandCarbonEntry.inventory_id==inventory.id)))
        return {"inventory_id": inventory.id, "summary": land_summary(entries), "entries": [{"id":e.id,"type":e.entry_type,"activity":e.activity_name,"quantity_tco2e":e.quantity_tco2e,"status":e.status} for e in entries]}
