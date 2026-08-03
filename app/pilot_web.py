from __future__ import annotations

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from .database import PilotSourceRequirement, add_audit, get_db
from .sector_library import build_pilot_workbook, pilot_summary
from .pilot_execution import pilot_execution_summary


def register_pilot_routes(app, templates, common_context, require_user, ensure_capability, set_flash) -> None:
    @app.get("/piloto-greenatics", response_class=HTMLResponse)
    def pilot_page(
        request: Request,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        if not ({"view_methodology", "provide_data"} & set(user["capabilities"])):
            raise HTTPException(403, "Tu rol no tiene permiso para consultar el piloto")
        summary = pilot_summary(session, int(user["organization_id"]))
        execution_summary = pilot_execution_summary(session, int(user["organization_id"]))
        session.commit()
        return templates.TemplateResponse(
            request=request,
            name="greenatics_pilot.html",
            context=common_context(request, session, user, "greenatics_pilot", summary=summary, execution_summary=execution_summary),
        )

    @app.post("/piloto-greenatics/fuentes/{requirement_id}")
    def update_pilot_requirement(
        requirement_id: int,
        request: Request,
        status: str = Form(...),
        data_owner: str = Form(""),
        notes: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        if not ({"manage_methodology_governance", "provide_data"} & set(user["capabilities"])):
            raise HTTPException(403, "Tu rol no tiene permiso para actualizar el piloto")
        allowed = {"Pendiente", "Solicitado", "Disponible", "Validado", "No aplica"}
        if status not in allowed:
            raise HTTPException(400, "Estado de información inválido")
        item = session.get(PilotSourceRequirement, requirement_id)
        if not item or item.pilot.organization_id != int(user["organization_id"]):
            raise HTTPException(404, "Fuente del piloto no encontrada")
        previous = f"{item.status} · {item.data_owner}"
        item.status = status
        item.data_owner = data_owner.strip() or item.data_owner
        item.notes = notes.strip()
        item.updated_by = str(user["email"])
        add_audit(
            session,
            int(user["organization_id"]),
            str(user["email"]),
            "ACTUALIZAR",
            "Fuente piloto Greenatics",
            item.code,
            previous_value=previous,
            new_value=f"{item.status} · {item.data_owner}",
            detail=item.notes,
        )
        session.commit()
        set_flash(request, f"Fuente {item.code} actualizada.")
        return RedirectResponse("/piloto-greenatics#fuentes", status_code=303)

    @app.get("/piloto-greenatics/exportar.xlsx")
    def export_pilot(
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        if not ({"view_methodology", "provide_data"} & set(user["capabilities"])):
            raise HTTPException(403, "Tu rol no tiene permiso para exportar el piloto")
        content = build_pilot_workbook(pilot_summary(session, int(user["organization_id"])))
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="piloto_greenatics_2026_v0_25.xlsx"'},
        )
