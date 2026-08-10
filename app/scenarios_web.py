from __future__ import annotations

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .database import add_audit, get_db
from .db.models import ReductionScenario, ReductionScenarioAction
from .scenarios import get_scenario, portfolio_macc, scenario_summary


def register_scenario_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash,
    get_inventory, ensure_inventory_editable
) -> None:
    @app.get("/escenarios", response_class=HTMLResponse)
    def scenarios_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        inventory = get_inventory(session, user)
        scenarios = list(session.scalars(
            select(ReductionScenario)
            .where(ReductionScenario.inventory_id == inventory.id)
            .options(selectinload(ReductionScenario.action_links).selectinload(ReductionScenarioAction.action))
            .order_by(ReductionScenario.created_at.desc())
        ))
        selected_id = request.query_params.get("scenario_id")
        selected = None
        if selected_id and selected_id.isdigit():
            selected = get_scenario(session, int(selected_id), int(user["organization_id"]))
        if not selected and scenarios:
            selected = get_scenario(session, scenarios[0].id, int(user["organization_id"]))
        selected_summary = scenario_summary(selected) if selected else None
        macc = portfolio_macc(inventory.reduction_actions, selected.discount_rate if selected else 10.0)
        return templates.TemplateResponse(
            request=request,
            name="scenarios.html",
            context=common_context(
                request, session, user, "scenarios", inventory=inventory, scenarios=scenarios,
                selected=selected, selected_summary=selected_summary, actions=inventory.reduction_actions,
                portfolio_macc=macc,
            ),
        )

    @app.post("/escenarios/nuevo")
    def create_scenario(
        request: Request, inventory_id: int = Form(...), name: str = Form(...), description: str = Form(""),
        start_year: int = Form(...), target_year: int = Form(...), discount_rate: float = Form(10.0),
        session: Session = Depends(get_db), user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_inventory")
        inventory = get_inventory(session, user, inventory_id)
        ensure_inventory_editable(inventory)
        if target_year < start_year:
            raise HTTPException(400, "El año objetivo no puede ser anterior al año inicial")
        scenario = ReductionScenario(
            inventory_id=inventory.id, name=name.strip(), description=description.strip(), start_year=start_year,
            target_year=target_year, discount_rate=max(0.0, discount_rate), status="Borrador", created_by=str(user["email"]),
        )
        session.add(scenario)
        session.flush()
        for action in inventory.reduction_actions:
            session.add(ReductionScenarioAction(
                scenario_id=scenario.id, action_id=action.id, included=False,
                implementation_year=action.implementation_year or start_year, adoption_percent=100.0,
            ))
        add_audit(session, int(user["organization_id"]), str(user["email"]), "CREAR", "Escenario", scenario.name, f"Periodo {start_year}-{target_year}")
        session.commit()
        set_flash(request, "Escenario creado. Selecciona las medidas que harán parte del portafolio.")
        return RedirectResponse(f"/escenarios?scenario_id={scenario.id}", status_code=303)

    @app.post("/escenarios/{scenario_id}/configurar")
    async def configure_scenario(
        scenario_id: int, request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_inventory")
        scenario = get_scenario(session, scenario_id, int(user["organization_id"]))
        if not scenario:
            raise HTTPException(404, "Escenario no encontrado")
        ensure_inventory_editable(scenario.inventory)
        form = await request.form()
        scenario.status = str(form.get("status") or scenario.status)
        discount_rate = float(form.get("discount_rate") or scenario.discount_rate)
        scenario.discount_rate = max(0.0, discount_rate)
        for link in scenario.action_links:
            link.included = f"include_{link.action_id}" in form
            try:
                link.adoption_percent = min(100.0, max(0.0, float(form.get(f"adoption_{link.action_id}") or 100)))
            except (TypeError, ValueError):
                link.adoption_percent = 100.0
            try:
                link.implementation_year = int(form.get(f"year_{link.action_id}") or scenario.start_year)
            except (TypeError, ValueError):
                link.implementation_year = scenario.start_year
        add_audit(session, int(user["organization_id"]), str(user["email"]), "CONFIGURAR", "Escenario", scenario.name, "Portafolio, adopción y cronograma actualizados")
        session.commit()
        set_flash(request, "Escenario recalculado correctamente.")
        return RedirectResponse(f"/escenarios?scenario_id={scenario.id}", status_code=303)
