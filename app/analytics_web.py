from __future__ import annotations

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .analytics import full_analysis
from .database import add_audit, get_db
from .db.models import ActivityIndicator, Inventory


def register_analytics_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash, parse_date,
    get_inventory, ensure_inventory_editable
) -> None:
    def _render_analysis(
        request: Request,
        session: Session,
        user: dict,
        inventory,
        *,
        scoped_workspace: bool,
    ):
        analysis = full_analysis(session, inventory)
        return templates.TemplateResponse(
            request=request,
            name="analysis.html",
            context=common_context(
                request, session, user, "analysis", inventory=inventory,
                indicator_types=[("Producción", "t"), ("Empleados", "personas"), ("Ingresos", "COP"), ("Servicios", "servicios"), ("Área", "m²")],
                scoped_workspace=scoped_workspace,
                **analysis,
            ),
        )

    @app.get("/analisis", response_class=HTMLResponse)
    def analysis_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        inventory = get_inventory(session, user)
        return _render_analysis(
            request,
            session,
            user,
            inventory,
            scoped_workspace=False,
        )

    @app.get("/inventarios/{inventory_id}/analisis", response_class=HTMLResponse)
    def inventory_analysis_page(
        inventory_id: int,
        request: Request,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        inventory = get_inventory(session, user, inventory_id)
        return _render_analysis(
            request,
            session,
            user,
            inventory,
            scoped_workspace=True,
        )

    @app.post("/analisis/indicadores/nuevo")
    def create_indicator(
        request: Request,
        inventory_id: int = Form(...),
        indicator_type: str = Form(...),
        value: float = Form(...),
        unit: str = Form(...),
        period_start: str = Form(...),
        period_end: str = Form(...),
        source_name: str = Form("Registro operativo"),
        facility_id: int | None = Form(None),
        notes: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_inventory")
        inventory = get_inventory(session, user, inventory_id)
        ensure_inventory_editable(inventory)
        if value < 0:
            raise HTTPException(400, "El valor del indicador no puede ser negativo")
        indicator = ActivityIndicator(
            inventory_id=inventory.id, facility_id=facility_id or None,
            period_start=parse_date(period_start), period_end=parse_date(period_end),
            indicator_type=indicator_type.strip(), value=value, unit=unit.strip(),
            source_name=source_name.strip() or "Registro operativo", notes=notes.strip(),
            status="Cargado", created_by=str(user["email"]),
        )
        session.add(indicator)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "CREAR", "Indicador", indicator.indicator_type, f"{value} {unit}")
        session.commit()
        set_flash(request, "Indicador operativo registrado.")
        return RedirectResponse("/analisis", status_code=303)

    @app.post("/analisis/indicadores/{indicator_id}/editar")
    def update_indicator(
        indicator_id: int, request: Request, value: float = Form(...), unit: str = Form(...),
        source_name: str = Form("Registro operativo"), notes: str = Form(""),
        session: Session = Depends(get_db), user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_inventory")
        indicator = session.scalar(
            select(ActivityIndicator).join(Inventory).where(
                ActivityIndicator.id == indicator_id, Inventory.organization_id == int(user["organization_id"])
            )
        )
        if not indicator:
            raise HTTPException(404, "Indicador no encontrado")
        inventory = get_inventory(session, user, indicator.inventory_id)
        ensure_inventory_editable(inventory)
        previous = f"{indicator.value} {indicator.unit}"
        indicator.value = value
        indicator.unit = unit.strip()
        indicator.source_name = source_name.strip() or indicator.source_name
        indicator.notes = notes.strip()
        add_audit(session, int(user["organization_id"]), str(user["email"]), "EDITAR", "Indicador", indicator.indicator_type, previous_value=previous, new_value=f"{value} {unit}")
        session.commit()
        set_flash(request, "Indicador actualizado.")
        return RedirectResponse("/analisis", status_code=303)
