from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi import Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .database import PilotExecution, PilotIssue, add_audit, get_db
from .pilot_execution import (
    build_pilot_execution_workbook,
    get_pilot_execution,
    import_pilot_comparison_workbook,
    import_pilot_workbook,
    pilot_execution_summary,
    start_pilot_execution,
    update_pilot_source_comparison,
)
from .security import validate_upload_bytes


def _date_or_none(value: str) -> date | None:
    value = value.strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(400, "Fecha inválida") from exc


def register_pilot_execution_routes(app, templates, common_context, require_user, set_flash) -> None:
    @app.get("/piloto-greenatics/ejecucion", response_class=HTMLResponse)
    def execution_page(
        request: Request,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        if not ({"view_methodology", "provide_data", "review", "approve"} & set(user["capabilities"])):
            raise HTTPException(403, "Tu rol no tiene permiso para consultar la ejecución del piloto")
        summary = pilot_execution_summary(session, int(user["organization_id"]))
        session.commit()
        import_errors = request.session.pop("pilot_import_errors", [])
        comparison_import_errors = request.session.pop("pilot_comparison_import_errors", [])
        return templates.TemplateResponse(
            request=request,
            name="greenatics_pilot_execution.html",
            context=common_context(request, session, user, "greenatics_pilot_execution", summary=summary, inventory=summary["inventory"], import_errors=import_errors, comparison_import_errors=comparison_import_errors),
        )

    @app.post("/piloto-greenatics/ejecucion/iniciar")
    def start_execution(
        request: Request,
        target_date: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        if not ({"manage_inventory", "manage_methodology_governance"} & set(user["capabilities"])):
            raise HTTPException(403, "Tu rol no puede iniciar el piloto")
        try:
            execution = start_pilot_execution(
                session,
                int(user["organization_id"]),
                str(user["email"]),
                str(user["name"]),
                _date_or_none(target_date),
            )
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        session.commit()
        set_flash(request, f"Piloto iniciado y vinculado al inventario #{execution.inventory_id}.")
        return RedirectResponse("/piloto-greenatics/ejecucion", status_code=303)

    @app.get("/piloto-greenatics/ejecucion/plantilla.xlsx")
    def execution_workbook(
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        if not ({"view_methodology", "provide_data"} & set(user["capabilities"])):
            raise HTTPException(403, "Tu rol no puede descargar la plantilla")
        summary = pilot_execution_summary(session, int(user["organization_id"]))
        if not summary["execution"]:
            raise HTTPException(409, "Primero debes iniciar el piloto")
        content = build_pilot_execution_workbook(summary)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="piloto_greenatics_v0_46_1_datos_y_contraste.xlsx"'},
        )

    @app.post("/piloto-greenatics/ejecucion/importar")
    async def import_execution_data(
        request: Request,
        file: UploadFile = File(...),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        if not ({"provide_data", "manage_inventory"} & set(user["capabilities"])):
            raise HTTPException(403, "Tu rol no puede importar datos del piloto")
        limit = settings.max_upload_mb * 1024 * 1024
        content = await file.read(limit + 1)
        if len(content) > limit:
            raise HTTPException(413, "El archivo supera el tamaño máximo permitido")
        ok, message, _ = validate_upload_bytes(file.filename or "datos.xlsx", content, file.content_type or "", {".xlsx"})
        if not ok:
            raise HTTPException(400, message)
        try:
            result = import_pilot_workbook(session, int(user["organization_id"]), content, str(user["email"]))
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        session.commit()
        detail = f"{result['imported']} creados, {result['updated']} actualizados"
        if result["errors"]:
            detail += f" y {len(result['errors'])} filas rechazadas"
        set_flash(request, f"Importación completada: {detail}.", "warning" if result["errors"] else "success")
        request.session["pilot_import_errors"] = result["errors"][:20]
        return RedirectResponse("/piloto-greenatics/ejecucion#datos", status_code=303)

    @app.post("/piloto-greenatics/ejecucion/contraste/importar")
    async def import_source_comparisons(
        request: Request,
        file: UploadFile = File(...),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        if not ({"manage_inventory", "review", "approve"} & set(user["capabilities"])):
            raise HTTPException(403, "Tu rol no puede importar el contraste")
        limit = settings.max_upload_mb * 1024 * 1024
        content = await file.read(limit + 1)
        if len(content) > limit:
            raise HTTPException(413, "El archivo supera el tamaño máximo permitido")
        ok, message, _ = validate_upload_bytes(file.filename or "contraste.xlsx", content, file.content_type or "", {".xlsx"})
        if not ok:
            raise HTTPException(400, message)
        try:
            result = import_pilot_comparison_workbook(session, int(user["organization_id"]), content, str(user["email"]))
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        session.commit()
        request.session["pilot_comparison_import_errors"] = result["errors"][:20]
        set_flash(request, f"Contraste importado: {result['updated']} fuente(s) actualizadas y {len(result['errors'])} fila(s) rechazadas.", "warning" if result["errors"] else "success")
        return RedirectResponse("/piloto-greenatics/ejecucion#contraste", status_code=303)

    @app.post("/piloto-greenatics/ejecucion/contraste/fuentes/{comparison_id}")
    def update_source_comparison(
        comparison_id: int,
        request: Request,
        independent_tco2e: float = Form(...),
        notes: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        if not ({"manage_inventory", "review", "approve"} & set(user["capabilities"])):
            raise HTTPException(403, "Tu rol no puede registrar el contraste")
        try:
            comparison = update_pilot_source_comparison(
                session, int(user["organization_id"]), comparison_id, independent_tco2e, notes, str(user["email"])
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        session.commit()
        set_flash(request, f"Fuente {comparison.requirement.code} contrastada: {comparison.status}.")
        return RedirectResponse("/piloto-greenatics/ejecucion#contraste", status_code=303)

    @app.post("/piloto-greenatics/ejecucion/contraste")
    def update_comparison(
        request: Request,
        independent_total_tco2e: float = Form(...),
        comparison_notes: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        if not ({"manage_inventory", "review", "approve"} & set(user["capabilities"])):
            raise HTTPException(403, "Tu rol no puede registrar el contraste")
        if independent_total_tco2e < 0:
            raise HTTPException(400, "El resultado independiente no puede ser negativo")
        execution = get_pilot_execution(session, int(user["organization_id"]))
        if not execution:
            raise HTTPException(404, "Ejecución del piloto no encontrada")
        previous = execution.independent_total_tco2e
        execution.independent_total_tco2e = independent_total_tco2e
        execution.comparison_notes = comparison_notes.strip()
        summary = pilot_execution_summary(session, int(user["organization_id"]))
        add_audit(
            session,
            int(user["organization_id"]),
            str(user["email"]),
            "CONTRASTAR",
            "Piloto Greenatics",
            execution.pilot.code,
            previous_value=str(previous or ""),
            new_value=f"{independent_total_tco2e} tCO2e · variación {summary['metrics']['variance']}%",
            detail=execution.comparison_notes,
        )
        session.commit()
        set_flash(request, f"Contraste registrado. Estado: {execution.comparison_status}.")
        return RedirectResponse("/piloto-greenatics/ejecucion#contraste", status_code=303)

    @app.post("/piloto-greenatics/ejecucion/incidencias")
    def create_issue(
        request: Request,
        category: str = Form("Datos"),
        title: str = Form(...),
        description: str = Form(""),
        severity: str = Form("Media"),
        owner: str = Form("Equipo piloto"),
        due_date: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        if not ({"manage_inventory", "review", "manage_methodology_governance"} & set(user["capabilities"])):
            raise HTTPException(403, "Tu rol no puede crear incidencias")
        execution = get_pilot_execution(session, int(user["organization_id"]))
        if not execution:
            raise HTTPException(404, "Ejecución del piloto no encontrada")
        sequence = session.scalar(select(PilotIssue.id).where(PilotIssue.execution_id == execution.id).order_by(PilotIssue.id.desc()).limit(1)) or 0
        issue = PilotIssue(
            execution_id=execution.id,
            code=f"PIL-025-{sequence + 1:03d}",
            category=category.strip() or "Datos",
            title=title.strip(),
            description=description.strip(),
            severity=severity if severity in {"Baja", "Media", "Alta", "Crítica"} else "Media",
            status="Abierto",
            owner=owner.strip() or "Equipo piloto",
            due_date=_date_or_none(due_date),
            created_by=str(user["email"]),
        )
        session.add(issue)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "CREAR", "Incidencia piloto", issue.code, detail=issue.title)
        session.commit()
        set_flash(request, f"Incidencia {issue.code} creada.")
        return RedirectResponse("/piloto-greenatics/ejecucion#incidencias", status_code=303)

    @app.post("/piloto-greenatics/ejecucion/incidencias/{issue_id}")
    def update_issue(
        issue_id: int,
        request: Request,
        status: str = Form(...),
        owner: str = Form(""),
        resolution: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        if not ({"manage_inventory", "review", "manage_methodology_governance"} & set(user["capabilities"])):
            raise HTTPException(403, "Tu rol no puede actualizar incidencias")
        issue = session.get(PilotIssue, issue_id)
        if not issue or issue.execution.pilot.organization_id != int(user["organization_id"]):
            raise HTTPException(404, "Incidencia no encontrada")
        if status not in {"Abierto", "En curso", "Resuelto", "Cerrado"}:
            raise HTTPException(400, "Estado inválido")
        previous = issue.status
        issue.status = status
        issue.owner = owner.strip() or issue.owner
        issue.resolution = resolution.strip()
        add_audit(
            session,
            int(user["organization_id"]),
            str(user["email"]),
            "ACTUALIZAR",
            "Incidencia piloto",
            issue.code,
            previous_value=previous,
            new_value=issue.status,
            detail=issue.resolution,
        )
        session.commit()
        set_flash(request, f"Incidencia {issue.code} actualizada.")
        return RedirectResponse("/piloto-greenatics/ejecucion#incidencias", status_code=303)

    @app.post("/piloto-greenatics/ejecucion/aprobar")
    def approve_execution(
        request: Request,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        if not ({"approve", "manage_methodology_governance"} & set(user["capabilities"])):
            raise HTTPException(403, "Tu rol no puede aprobar el piloto")
        summary = pilot_execution_summary(session, int(user["organization_id"]))
        execution: PilotExecution | None = summary["execution"]
        if not execution:
            raise HTTPException(404, "Ejecución del piloto no encontrada")
        if summary["blockers"]:
            raise HTTPException(409, "No es posible aprobar: " + " ".join(summary["blockers"]))
        execution.status = "Aprobado"
        execution.approved_by = str(user["email"])
        execution.approved_at = datetime.now(UTC)
        execution.pilot.status = "Piloto aprobado"
        if execution.inventory:
            execution.inventory.status = "Aprobado"
            execution.inventory.current_stage = "Piloto validado"
        add_audit(session, int(user["organization_id"]), str(user["email"]), "APROBAR", "Piloto Greenatics", execution.pilot.code, detail="Piloto aprobado después de contraste independiente y cierre de incidencias.")
        session.commit()
        set_flash(request, "Piloto aprobado y registrado en auditoría.")
        return RedirectResponse("/piloto-greenatics/ejecucion#cierre", status_code=303)
