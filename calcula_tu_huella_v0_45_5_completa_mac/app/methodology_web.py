from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import FactorDocumentation, FactorSelectionRule, add_audit, get_db
from .methodology_core import (
    build_methodology_workbook,
    methodology_summary,
    run_reference_suite,
    summary_json,
)


def register_methodology_core_routes(app, templates, common_context, require_user, ensure_capability, set_flash) -> None:
    @app.get("/metodologia/nucleo", response_class=HTMLResponse)
    def methodology_core_page(
        request: Request,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "view_methodology")
        summary = methodology_summary(session)
        return templates.TemplateResponse(
            request=request,
            name="methodology_core.html",
            context=common_context(request, session, user, "methodology_core", summary=summary),
        )

    @app.post("/metodologia/nucleo/validar")
    def methodology_core_validate(
        request: Request,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_methodology_governance")
        run = run_reference_suite(session, str(user["email"]))
        add_audit(
            session,
            int(user["organization_id"]),
            str(user["email"]),
            "VALIDAR",
            "Núcleo metodológico",
            run.run_code,
            f"Motor {run.engine_version} · {run.passed_cases}/{run.total_cases} casos aprobados",
        )
        session.commit()
        level = "success" if run.status == "Aprobado" else "error"
        set_flash(request, f"Validación {run.run_code}: {run.passed_cases} aprobados y {run.failed_cases} fallidos.", level)
        return RedirectResponse("/metodologia/nucleo#casos", status_code=303)

    @app.post("/metodologia/nucleo/factores/{documentation_id}/revisar")
    def methodology_factor_review(
        documentation_id: int,
        request: Request,
        review_status: str = Form(...),
        quality_grade: str = Form(...),
        reporting_use: str = Form(...),
        restriction_notes: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "review")
        if review_status not in {"Pendiente", "En revisión", "Aprobado documentalmente", "Rechazado", "Demostrativo"}:
            raise HTTPException(400, "Estado documental inválido")
        if quality_grade not in {"A", "B", "C", "D", "N/A"}:
            raise HTTPException(400, "Calidad inválida")
        if reporting_use not in {"Formal", "Piloto", "Demostrativo", "Retirado"}:
            raise HTTPException(400, "Uso metodológico inválido")
        documentation = session.get(FactorDocumentation, documentation_id)
        if not documentation:
            raise HTTPException(404, "Documentación de factor no encontrada")
        previous = f"{documentation.review_status} · {documentation.reporting_use} · {documentation.quality_grade}"
        documentation.review_status = review_status
        documentation.quality_grade = quality_grade
        documentation.reporting_use = reporting_use
        documentation.restriction_notes = restriction_notes.strip()
        documentation.reviewer = str(user["email"])
        documentation.reviewed_at = datetime.now(UTC)
        add_audit(
            session,
            int(user["organization_id"]),
            str(user["email"]),
            "REVISAR",
            "Documentación de factor",
            str(documentation.factor_version_id),
            previous_value=previous,
            new_value=f"{review_status} · {reporting_use} · {quality_grade}",
            detail=documentation.restriction_notes,
        )
        session.commit()
        set_flash(request, "La clasificación documental del factor fue actualizada.")
        return RedirectResponse("/metodologia/nucleo#factores", status_code=303)

    @app.post("/metodologia/nucleo/reglas/{rule_id}/estado")
    def methodology_rule_status(
        rule_id: int,
        request: Request,
        status: str = Form(...),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_methodology_governance")
        if status not in {"Activa", "En revisión", "Inactiva"}:
            raise HTTPException(400, "Estado de regla inválido")
        rule = session.scalar(select(FactorSelectionRule).where(FactorSelectionRule.id == rule_id))
        if not rule:
            raise HTTPException(404, "Regla no encontrada")
        previous = rule.status
        rule.status = status
        add_audit(
            session,
            int(user["organization_id"]),
            str(user["email"]),
            "ACTUALIZAR",
            "Regla de selección de factor",
            rule.code,
            previous_value=previous,
            new_value=status,
            detail=rule.name,
        )
        session.commit()
        set_flash(request, f"Regla {rule.code} actualizada.")
        return RedirectResponse("/metodologia/nucleo#reglas", status_code=303)

    @app.get("/metodologia/nucleo/exportar.xlsx")
    def methodology_core_export(
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "view_methodology")
        content = build_methodology_workbook(methodology_summary(session))
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="nucleo_metodologico_v0_28.xlsx"'},
        )

    @app.get("/api/metodologia/nucleo")
    def methodology_core_api(
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "view_methodology")
        return Response(content=summary_json(methodology_summary(session)), media_type="application/json")
