from __future__ import annotations

from fastapi import Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from .data_quality import (
    apply_import_batch,
    build_data_template,
    build_quality_report,
    create_import_batch,
    data_quality_summary,
    resolve_finding,
)
from .database import get_db
from .security import validate_upload_bytes


def register_data_quality_routes(app, templates, common_context, require_user, set_flash) -> None:
    def _can_view(user: dict) -> bool:
        capabilities = set(user["capabilities"])
        return bool({"provide_data", "manage_inventory", "review", "approve", "view_methodology"} & capabilities)

    def _can_manage(user: dict) -> bool:
        capabilities = set(user["capabilities"])
        return bool({"manage_inventory", "review", "approve"} & capabilities)

    @app.get("/calidad-datos", response_class=HTMLResponse)
    def quality_page(
        request: Request,
        batch_id: int | None = None,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        if not _can_view(user):
            raise HTTPException(403, "Tu rol no puede consultar la calidad de datos")
        summary = data_quality_summary(session, int(user["organization_id"]), batch_id)
        return templates.TemplateResponse(
            request=request,
            name="data_quality.html",
            context=common_context(
                request,
                session,
                user,
                "data_quality",
                summary=summary,
                can_manage=_can_manage(user),
            ),
        )

    @app.get("/calidad-datos/plantilla.xlsx")
    def quality_template(session: Session = Depends(get_db), user: dict = Depends(require_user)):
        if not _can_view(user):
            raise HTTPException(403, "Tu rol no puede descargar la plantilla")
        try:
            content = build_data_template(session, int(user["organization_id"]))
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="plantilla_datos_reales_greenatics_v0_26.xlsx"'},
        )

    @app.post("/calidad-datos/cargar")
    async def upload_quality_batch(
        request: Request,
        file: UploadFile = File(...),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        if not _can_manage(user):
            raise HTTPException(403, "Tu rol no puede cargar lotes")
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(413, "El archivo supera 10 MB")
        filename = file.filename or "carga.xlsx"
        valid, message, _ = validate_upload_bytes(filename, content, file.content_type, {".xlsx"})
        if not valid:
            raise HTTPException(400, message)
        try:
            batch = create_import_batch(
                session,
                int(user["organization_id"]),
                filename,
                content,
                str(user["email"]),
            )
            session.commit()
        except ValueError as exc:
            session.rollback()
            raise HTTPException(409, str(exc)) from exc
        level = "warning" if batch.error_rows or batch.warning_rows else "success"
        set_flash(
            request,
            f"Lote {batch.code} validado: {batch.valid_rows} filas válidas, {batch.warning_rows} advertencias y {batch.error_rows} errores.",
            level,
        )
        return RedirectResponse(f"/calidad-datos?batch_id={batch.id}", status_code=303)

    @app.post("/calidad-datos/lotes/{batch_id}/aplicar")
    def apply_quality_batch(
        batch_id: int,
        request: Request,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        if not _can_manage(user):
            raise HTTPException(403, "Tu rol no puede aplicar lotes")
        try:
            batch = apply_import_batch(session, int(user["organization_id"]), batch_id, str(user["email"]))
            session.commit()
        except ValueError as exc:
            session.rollback()
            raise HTTPException(409, str(exc)) from exc
        set_flash(request, f"Lote {batch.code} aplicado: {batch.applied_rows} registros actualizados.")
        return RedirectResponse(f"/calidad-datos?batch_id={batch.id}", status_code=303)

    @app.post("/calidad-datos/hallazgos/{finding_id}/cerrar")
    def close_quality_finding(
        finding_id: int,
        request: Request,
        resolution: str = Form(...),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        if not _can_manage(user):
            raise HTTPException(403, "Tu rol no puede cerrar hallazgos")
        try:
            finding = resolve_finding(
                session,
                int(user["organization_id"]),
                finding_id,
                resolution,
                str(user["email"]),
            )
            session.commit()
        except ValueError as exc:
            session.rollback()
            raise HTTPException(404, str(exc)) from exc
        set_flash(request, f"Hallazgo {finding.rule_code} cerrado.")
        return RedirectResponse(f"/calidad-datos?batch_id={finding.batch_id}#hallazgos", status_code=303)

    @app.get("/calidad-datos/reporte.xlsx")
    def quality_report(session: Session = Depends(get_db), user: dict = Depends(require_user)):
        if not _can_view(user):
            raise HTTPException(403, "Tu rol no puede exportar el reporte")
        summary = data_quality_summary(session, int(user["organization_id"]))
        content = build_quality_report(summary)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="reporte_calidad_datos_v0_26.xlsx"'},
        )
