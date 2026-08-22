from __future__ import annotations

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .analytics import reduction_summary
from .database import EmissionTarget, Inventory, ReductionAction, add_audit, get_db
from .reduction_portfolio import build_portfolio_workbook, portfolio_json, portfolio_summary


def register_reduction_routes(
    app,
    templates,
    common_context,
    require_user,
    ensure_capability,
    set_flash,
    parse_date,
    get_inventory,
    get_source_for_user,
    ensure_inventory_editable,
    inventory_metrics,
) -> None:
    @app.post("/reduccion/metas/nueva")
    def create_emission_target(request: Request, inventory_id: int = Form(...), name: str = Form(...), metric_type: str = Form("Absoluta"), baseline_year: int = Form(...), target_year: int = Form(...), baseline_value: float = Form(...), target_value: float = Form(...), unit: str = Form("tCO₂e"), notes: str = Form(""), session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_inventory")
        inventory = get_inventory(session, user, inventory_id)
        ensure_inventory_editable(inventory)
        if target_year <= baseline_year:
            raise HTTPException(400, "El año meta debe ser posterior al año base")
        if baseline_value <= 0 or target_value < 0 or target_value >= baseline_value:
            raise HTTPException(400, "La meta debe representar una reducción frente a la línea base")
        target = EmissionTarget(inventory_id=inventory.id, name=name.strip(), metric_type=metric_type, baseline_year=baseline_year, target_year=target_year, baseline_value=baseline_value, target_value=target_value, current_value=inventory_metrics(inventory)["total"] if metric_type == "Absoluta" else baseline_value, unit=unit.strip(), status="Activa", notes=notes.strip(), created_by=str(user["email"]))
        session.add(target)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "CREAR", "Meta climática", target.name, f"{target_value} {unit} al {target_year}")
        session.commit()
        set_flash(request, "Meta climática creada.")
        return RedirectResponse("/reduccion", status_code=303)

    @app.post("/reduccion/metas/{target_id}/actualizar")
    def update_emission_target(target_id: int, request: Request, current_value: float = Form(...), status: str = Form(...), notes: str = Form(""), session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_inventory")
        target = session.scalar(select(EmissionTarget).join(Inventory).where(EmissionTarget.id == target_id, Inventory.organization_id == int(user["organization_id"])))
        if not target:
            raise HTTPException(404, "Meta no encontrada")
        inventory = get_inventory(session, user, target.inventory_id)
        ensure_inventory_editable(inventory)
        target.current_value = max(current_value, 0)
        target.status = status
        target.notes = notes.strip()
        add_audit(session, int(user["organization_id"]), str(user["email"]), "EDITAR", "Meta climática", target.name, f"Valor actual {target.current_value} {target.unit}")
        session.commit()
        set_flash(request, "Meta actualizada.")
        return RedirectResponse("/reduccion", status_code=303)

    @app.post("/reduccion/metas/{target_id}/sincronizar")
    def sync_emission_target(target_id: int, request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_inventory")
        target = session.scalar(select(EmissionTarget).join(Inventory).where(EmissionTarget.id == target_id, Inventory.organization_id == int(user["organization_id"])))
        if not target:
            raise HTTPException(404, "Meta no encontrada")
        inventory = get_inventory(session, user, target.inventory_id)
        ensure_inventory_editable(inventory)
        if target.metric_type == "Absoluta":
            target.current_value = float(inventory_metrics(inventory)["total"])
        add_audit(session, int(user["organization_id"]), str(user["email"]), "SINCRONIZAR", "Meta climática", target.name, f"Valor actual {target.current_value} {target.unit}")
        session.commit()
        set_flash(request, "Meta sincronizada con el inventario actual.")
        return RedirectResponse("/reduccion", status_code=303)

    @app.post("/reduccion/acciones/nueva")
    def create_reduction_action(
        request: Request, inventory_id: int = Form(...), title: str = Form(...), description: str = Form(""),
        source_id: int | None = Form(None), expected_reduction: float = Form(0), investment_cost: float = Form(0),
        annual_savings: float = Form(0), priority: str = Form("Media"), responsible: str = Form(""),
        target_date: str = Form(""), status: str = Form("Identificada"), useful_life_years: int = Form(5),
        implementation_year: int | None = Form(None), feasibility: str = Form("Media"), risk_level: str = Form("Medio"),
        session: Session = Depends(get_db), user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_inventory")
        inventory = get_inventory(session, user, inventory_id)
        ensure_inventory_editable(inventory)
        source = get_source_for_user(session, user, source_id) if source_id else None
        if source and source.inventory_id != inventory.id:
            raise HTTPException(400, "La fuente no pertenece al inventario")
        action = ReductionAction(
            inventory_id=inventory.id, source_id=source_id or None, title=title.strip(), description=description.strip(),
            baseline_emissions=source.emissions if source else inventory_metrics(inventory)["total"],
            expected_reduction=max(expected_reduction, 0), investment_cost=max(investment_cost, 0),
            annual_savings=max(annual_savings, 0), priority=priority, responsible=responsible.strip(),
            target_date=parse_date(target_date) if target_date else None, status=status, progress_percent=0,
            useful_life_years=max(1, useful_life_years), implementation_year=implementation_year,
            feasibility=feasibility, risk_level=risk_level, created_by=str(user["email"]),
        )
        session.add(action)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "CREAR", "Acción de reducción", action.title, f"Reducción esperada {action.expected_reduction} tCO2e")
        session.commit()
        set_flash(request, "Acción de reducción creada.")
        return RedirectResponse("/reduccion", status_code=303)

    @app.post("/reduccion/acciones/{action_id}/actualizar")
    def update_reduction_action(
        action_id: int, request: Request, status: str = Form(...), progress_percent: int = Form(...),
        expected_reduction: float = Form(...), investment_cost: float = Form(...), annual_savings: float = Form(...),
        actual_reduction: float = Form(0), actual_savings: float = Form(0), responsible: str = Form(""),
        useful_life_years: int = Form(5), implementation_year: int | None = Form(None),
        feasibility: str = Form("Media"), risk_level: str = Form("Medio"),
        session: Session = Depends(get_db), user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_inventory")
        action = session.scalar(
            select(ReductionAction).join(Inventory).where(
                ReductionAction.id == action_id, Inventory.organization_id == int(user["organization_id"])
            )
        )
        if not action:
            raise HTTPException(404, "Acción no encontrada")
        inventory = get_inventory(session, user, action.inventory_id)
        ensure_inventory_editable(inventory)
        action.status = status
        action.progress_percent = min(100, max(0, progress_percent))
        action.expected_reduction = max(expected_reduction, 0)
        action.investment_cost = max(investment_cost, 0)
        action.annual_savings = max(annual_savings, 0)
        action.actual_reduction = max(actual_reduction, 0)
        action.actual_savings = max(actual_savings, 0)
        action.responsible = responsible.strip()
        action.useful_life_years = max(1, useful_life_years)
        action.implementation_year = implementation_year
        action.feasibility = feasibility
        action.risk_level = risk_level
        add_audit(session, int(user["organization_id"]), str(user["email"]), "EDITAR", "Acción de reducción", action.title, f"Estado {status}; avance {action.progress_percent}%")
        session.commit()
        set_flash(request, "Acción actualizada.")
        return RedirectResponse("/reduccion", status_code=303)

    def _render_reduction(
        request: Request,
        session: Session,
        user: dict,
        inventory,
        *,
        scoped_workspace: bool,
    ):
        legacy_summary = reduction_summary(session, inventory.id)
        portfolio = portfolio_summary(session, inventory)
        render_user = user
        if scoped_workspace:
            render_user = dict(user)
            render_user["can_manage_inventory"] = False
        return templates.TemplateResponse(
            request=request,
            name="reduction.html",
            context=common_context(
                request, session, render_user, "reduction", inventory=inventory, sources=inventory.sources,
                targets=inventory.targets, portfolio=portfolio, scoped_workspace=scoped_workspace, **legacy_summary,
            ),
        )

    @app.get("/reduccion", response_class=HTMLResponse)
    def reduction_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        inventory = get_inventory(session, user)
        return _render_reduction(
            request,
            session,
            user,
            inventory,
            scoped_workspace=False,
        )

    @app.get("/inventarios/{inventory_id}/reduccion", response_class=HTMLResponse)
    def inventory_reduction_page(
        inventory_id: int,
        request: Request,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        inventory = get_inventory(session, user, inventory_id)
        return _render_reduction(
            request,
            session,
            user,
            inventory,
            scoped_workspace=True,
        )

    @app.get("/api/reduccion/resumen")
    def reduction_portfolio_api(session: Session = Depends(get_db), user: dict = Depends(require_user)):
        inventory = get_inventory(session, user)
        return portfolio_json(portfolio_summary(session, inventory))

    @app.get("/reduccion/exportar.xlsx")
    def export_reduction_portfolio(session: Session = Depends(get_db), user: dict = Depends(require_user)):
        inventory = get_inventory(session, user)
        payload = build_portfolio_workbook(inventory, portfolio_summary(session, inventory))
        safe_year = inventory.start_date.year
        return Response(
            payload,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=portafolio_reduccion_{safe_year}.xlsx"},
        )
