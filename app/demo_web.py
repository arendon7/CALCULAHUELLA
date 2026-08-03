from __future__ import annotations

import json

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .database import DemoEnvironmentCertification, get_db
from .demo_environment import (
    certify_demo_environment,
    demo_environment_summary,
    ensure_demo_environment,
    resolve_demo_certificate,
)


def register_demo_routes(app, templates, common_context, require_user, ensure_capability, set_flash) -> None:
    @app.get("/entorno-demo", response_class=HTMLResponse)
    def demo_environment_page(
        request: Request,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_portfolio")
        summary = demo_environment_summary(session)
        certifications = []
        for item in summary["certifications"]:
            certifications.append({
                "row": item,
                "checks": json.loads(item.checks_json or "[]"),
                "summary": json.loads(item.summary_json or "{}"),
            })
        return templates.TemplateResponse(
            request=request,
            name="demo_environment.html",
            context=common_context(
                request,
                session,
                user,
                "demo_environment",
                summary=summary,
                certifications=certifications,
                demo_enabled=settings.seed_demo,
            ),
        )

    @app.post("/entorno-demo/preparar")
    def prepare_demo_environment(
        request: Request,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_portfolio")
        if not settings.seed_demo:
            raise HTTPException(409, "El modo demo está desactivado.")
        result = ensure_demo_environment(session)
        session.commit()
        totals = result["summary"]["totals"]
        set_flash(
            request,
            f"Entorno demo preparado: {result['summary']['organization_count']} empresas, "
            f"{totals['activity_records']} registros y {totals['calculations']} cálculos.",
        )
        return RedirectResponse("/entorno-demo", status_code=303)

    @app.post("/entorno-demo/certificar")
    def certify_demo(
        request: Request,
        notes: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_portfolio")
        if not settings.seed_demo:
            raise HTTPException(409, "El modo demo está desactivado.")
        certification = certify_demo_environment(
            session,
            int(user["organization_id"]),
            str(user["email"]),
            notes,
        )
        session.commit()
        set_flash(request, f"Certificación demo: {certification.status} · {certification.certificate_hash[:12]}…")
        return RedirectResponse("/entorno-demo#certificaciones", status_code=303)

    @app.get("/entorno-demo/certificados/{certification_id}/descargar")
    def download_demo_certificate(
        certification_id: int,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_portfolio")
        item = session.scalar(select(DemoEnvironmentCertification).where(DemoEnvironmentCertification.id == certification_id))
        if not item:
            raise HTTPException(404, "Certificación no encontrada")
        try:
            path = resolve_demo_certificate(item.artifact_name)
        except FileNotFoundError as exc:
            raise HTTPException(404, "El archivo de certificación no está disponible") from exc
        return FileResponse(path, filename=path.name, media_type="application/json")
