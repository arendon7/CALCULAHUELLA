from __future__ import annotations

from fastapi import Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from .calculations import recalculate_inventory, source_calculation_summary
from .database import add_audit, get_db
from .inventory_context import inventory_metrics


def register_calculation_routes(
    app,
    templates,
    common_context,
    require_user,
    ensure_capability,
    set_flash,
    get_inventory,
    ensure_inventory_editable,
) -> None:
    def _render_calculations(
        request: Request,
        session: Session,
        user: dict,
        inventory,
        *,
        scoped_workspace: bool,
    ):
        source_rows = []
        total_calculations = 0
        total_alerts = 0
        total_errors = 0
        for source in inventory.sources:
            summary = source_calculation_summary(session, source.id)
            source_rows.append(
                {
                    "source": source,
                    "summary": summary,
                    "assignments": len([item for item in source.factor_assignments if item.active]),
                }
            )
            total_calculations += len(summary["calculations"])
            total_alerts += int(summary["alerts"])
            total_errors += int(summary["errors"])
        metrics = inventory_metrics(inventory)
        return templates.TemplateResponse(
            request=request,
            name="calculations.html",
            context=common_context(
                request,
                session,
                user,
                "calculations",
                inventory=inventory,
                source_rows=source_rows,
                total_calculations=total_calculations,
                total_alerts=total_alerts,
                total_errors=total_errors,
                scoped_workspace=scoped_workspace,
                **metrics,
            ),
        )

    @app.get("/calculos", response_class=HTMLResponse)
    def calculations_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        inventory = get_inventory(session, user)
        return _render_calculations(
            request,
            session,
            user,
            inventory,
            scoped_workspace=False,
        )

    @app.get("/inventarios/{inventory_id}/calculos", response_class=HTMLResponse)
    def inventory_calculations_page(
        inventory_id: int,
        request: Request,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        inventory = get_inventory(session, user, inventory_id)
        return _render_calculations(
            request,
            session,
            user,
            inventory,
            scoped_workspace=True,
        )

    @app.post("/inventarios/{inventory_id}/recalcular")
    def inventory_recalculate(inventory_id: int, request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "view_methodology")
        inventory = get_inventory(session, user, inventory_id)
        ensure_inventory_editable(inventory)
        result = recalculate_inventory(session, inventory)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "RECALCULAR", "Inventario", inventory.name, f"{result['sources']} fuentes · {result['calculations']} cálculos · {len(result['warnings'])} alertas")
        session.commit()
        set_flash(request, f"Inventario recalculado: {result['calculations']} componentes y {len(result['warnings'])} alertas.", "error" if result["warnings"] else "success")
        return RedirectResponse("/calculos", status_code=303)
