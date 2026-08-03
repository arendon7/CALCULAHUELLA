from __future__ import annotations

import json
from datetime import UTC, date, datetime

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .accounting import ACCOUNTING_TREATMENTS, SCOPE2_METHODS
from .calculations import recalculate_source
from .database import BaseYearRecalculation, EmissionSource, add_audit, get_db
from .methodology_closure import closure_summary, create_recalculation, save_policy


def register_methodology_closure_routes(
    app,
    templates,
    common_context,
    require_user,
    ensure_capability,
    set_flash,
    get_inventory,
    ensure_inventory_editable,
) -> None:
    @app.get("/metodologia/cierre", response_class=HTMLResponse)
    def methodology_closure_page(
        request: Request,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "view_methodology")
        inventory = get_inventory(session, user)
        summary = closure_summary(session, inventory)
        session.commit()
        return templates.TemplateResponse(
            request=request,
            name="methodology_closure.html",
            context=common_context(request, session, user, "methodology_closure", summary=summary, inventory=inventory),
        )

    @app.post("/metodologia/cierre/politica")
    def methodology_closure_policy(
        request: Request,
        base_year_recalculation_threshold: float = Form(5.0),
        base_year_triggers: str = Form(""),
        biogenic_co2_policy: str = Form(""),
        removals_policy: str = Form(""),
        avoided_emissions_policy: str = Form(""),
        offsets_policy: str = Form(""),
        scope2_policy: str = Form(""),
        uncertainty_method: str = Form(""),
        action: str = Form("save"),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_methodology_governance")
        inventory = get_inventory(session, user)
        payload = {
            "base_year_recalculation_threshold": base_year_recalculation_threshold,
            "base_year_triggers": base_year_triggers.strip(),
            "biogenic_co2_policy": biogenic_co2_policy.strip(),
            "removals_policy": removals_policy.strip(),
            "avoided_emissions_policy": avoided_emissions_policy.strip(),
            "offsets_policy": offsets_policy.strip(),
            "scope2_policy": scope2_policy.strip(),
            "uncertainty_method": uncertainty_method.strip(),
        }
        approve = action == "approve"
        snapshot = save_policy(session, inventory, payload, str(user["email"]), approve=approve)
        add_audit(
            session,
            int(user["organization_id"]),
            str(user["email"]),
            "APROBAR" if approve else "ACTUALIZAR",
            "Política metodológica",
            snapshot.snapshot_name,
            new_value=snapshot.status,
            detail=f"Umbral de recalculo {base_year_recalculation_threshold:.2f}%",
        )
        session.commit()
        set_flash(request, "Política metodológica aprobada." if approve else "Política metodológica guardada.")
        return RedirectResponse("/metodologia/cierre#politica", status_code=303)

    @app.post("/metodologia/cierre/fuentes/{source_id}")
    def methodology_closure_source(
        source_id: int,
        request: Request,
        accounting_treatment: str = Form(...),
        scope2_method: str = Form("No aplica"),
        biogenic_origin: str = Form("No aplica"),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_methodology_governance")
        inventory = get_inventory(session, user)
        source = session.scalar(select(EmissionSource).where(EmissionSource.id == source_id, EmissionSource.inventory_id == inventory.id))
        if not source:
            raise HTTPException(404, "Fuente no encontrada")
        ensure_inventory_editable(inventory)
        if accounting_treatment not in ACCOUNTING_TREATMENTS:
            raise HTTPException(400, "Tratamiento contable inválido")
        if scope2_method not in SCOPE2_METHODS:
            raise HTTPException(400, "Método de alcance 2 inválido")
        if source.scope != 2:
            scope2_method = "No aplica"
        previous = f"{source.accounting_treatment} · {source.scope2_method} · {source.biogenic_origin}"
        source.accounting_treatment = accounting_treatment
        source.scope2_method = scope2_method
        source.biogenic_origin = biogenic_origin.strip() or "No aplica"
        session.flush()
        calculation_result = recalculate_source(session, source)
        add_audit(
            session,
            int(user["organization_id"]),
            str(user["email"]),
            "CLASIFICAR",
            "Fuente de emisión",
            source.name,
            previous_value=previous,
            new_value=f"{source.accounting_treatment} · {source.scope2_method} · {source.biogenic_origin}",
            detail=f"Clasificación metodológica V0.32 · {calculation_result['calculations']} cálculos actualizados",
        )
        session.commit()
        set_flash(request, f"Fuente {source.name} clasificada.")
        return RedirectResponse("/metodologia/cierre#fuentes", status_code=303)

    @app.post("/metodologia/cierre/recalculos")
    def methodology_closure_recalculation_create(
        request: Request,
        trigger_type: str = Form(...),
        description: str = Form(""),
        previous_total_tco2e: float = Form(...),
        recalculated_total_tco2e: float = Form(...),
        threshold_percentage: float = Form(5.0),
        event_date: date = Form(...),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_methodology_governance")
        inventory = get_inventory(session, user)
        item = create_recalculation(
            session,
            inventory,
            trigger_type=trigger_type,
            description=description,
            previous_total_tco2e=previous_total_tco2e,
            recalculated_total_tco2e=recalculated_total_tco2e,
            threshold_percentage=threshold_percentage,
            actor=str(user["email"]),
        )
        item.event_date = event_date
        add_audit(
            session,
            int(user["organization_id"]),
            str(user["email"]),
            "EVALUAR",
            "Recalculo de año base",
            str(item.id),
            new_value=f"{item.change_percentage:.2f}% · {item.decision}",
            detail=item.trigger_type,
        )
        session.commit()
        set_flash(request, f"Evento evaluado: {item.decision} ({item.change_percentage:.2f}%).")
        return RedirectResponse("/metodologia/cierre#anio-base", status_code=303)

    @app.post("/metodologia/cierre/recalculos/{item_id}/revisar")
    def methodology_closure_recalculation_review(
        item_id: int,
        request: Request,
        status: str = Form(...),
        decision: str = Form(...),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "review")
        inventory = get_inventory(session, user)
        item = session.scalar(select(BaseYearRecalculation).where(BaseYearRecalculation.id == item_id, BaseYearRecalculation.inventory_id == inventory.id))
        if not item:
            raise HTTPException(404, "Evaluación no encontrada")
        if status not in {"Pendiente", "Aprobado", "Rechazado"}:
            raise HTTPException(400, "Estado inválido")
        if decision not in {"Evaluar", "Recalcular", "No recalcular"}:
            raise HTTPException(400, "Decisión inválida")
        item.status = status
        item.decision = decision
        item.reviewed_by = str(user["email"])
        item.reviewed_at = datetime.now(UTC)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "REVISAR", "Recalculo de año base", str(item.id), new_value=f"{status} · {decision}", detail=item.trigger_type)
        session.commit()
        set_flash(request, "La evaluación de año base fue revisada.")
        return RedirectResponse("/metodologia/cierre#anio-base", status_code=303)

    @app.get("/api/metodologia/cierre")
    def methodology_closure_api(
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "view_methodology")
        inventory = get_inventory(session, user)
        summary = closure_summary(session, inventory)
        session.commit()
        payload = {
            "inventory_id": inventory.id,
            "readiness_score": summary["readiness_score"],
            "policy_status": summary["policy"]["status"],
            "balance": summary["balance"],
            "uncertainty": summary["uncertainty"],
            "scope2": {
                "location_based": summary["scope2"]["location_based"],
                "market_based": summary["scope2"]["market_based"],
                "unclassified": len(summary["scope2"]["unclassified"]),
            },
            "readiness": summary["readiness"],
        }
        return Response(content=json.dumps(payload, ensure_ascii=False), media_type="application/json")
