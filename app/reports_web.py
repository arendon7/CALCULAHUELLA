from __future__ import annotations

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from .analytics import full_analysis
from .database import get_db
from .repositories.reports import get_report_artifact, list_report_artifacts
from .services.reports import approve_report as approve_report_record
from .services.reports import generate_report as generate_report_record
from .storage import storage


def register_report_routes(
    app,
    templates,
    common_context,
    require_user,
    ensure_capability,
    set_flash,
    get_inventory,
) -> None:
    @app.get("/reportes", response_class=HTMLResponse)
    def reports(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        inventory = get_inventory(session, user)
        analysis = full_analysis(session, inventory)
        artifacts = list_report_artifacts(session, inventory.id)
        return templates.TemplateResponse(
            request=request,
            name="reports.html",
            context=common_context(request, session, user, "reports", inventory=inventory, artifacts=artifacts, **analysis),
        )


    @app.post("/reportes/generar")
    def generate_report(
        request: Request, inventory_id: int = Form(...), report_type: str = Form(...),
        session: Session = Depends(get_db), user: dict = Depends(require_user),
    ):
        if not (user["can_manage_inventory"] or user["can_review"]):
            raise HTTPException(403, "Tu rol no puede generar informes")
        inventory = get_inventory(session, user, inventory_id)
        try:
            artifact = generate_report_record(
                session,
                inventory,
                report_type,
                actor_email=str(user["email"]),
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        session.commit()
        set_flash(request, f"{artifact.report_type} generado correctamente.")
        return RedirectResponse("/reportes", status_code=303)


    @app.get("/reportes/{artifact_id}/descargar")
    def download_report(artifact_id: int, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        artifact = get_report_artifact(session, int(user["organization_id"]), artifact_id)
        if not artifact:
            raise HTTPException(404, "Informe no encontrado")
        if not storage.exists(artifact.stored_name):
            raise HTTPException(404, "El archivo del informe no está disponible")
        local_path = storage.local_path(artifact.stored_name)
        if local_path:
            media_types = {
                ".pdf": "application/pdf",
                ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ".zip": "application/zip",
            }
            return FileResponse(local_path, filename=artifact.file_name, media_type=media_types.get(local_path.suffix.lower(), "application/octet-stream"))
        return RedirectResponse(storage.presigned_url(artifact.stored_name), status_code=302)


    @app.post("/reportes/{artifact_id}/aprobar")
    def approve_report(
        artifact_id: int, request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user),
    ):
        ensure_capability(user, "approve")
        artifact = get_report_artifact(session, int(user["organization_id"]), artifact_id)
        if not artifact:
            raise HTTPException(404, "Informe no encontrado")
        approve_report_record(
            session,
            artifact,
            organization_id=int(user["organization_id"]),
            actor_email=str(user["email"]),
        )
        session.commit()
        set_flash(request, "Informe aprobado y versionado.")
        return RedirectResponse("/reportes", status_code=303)

