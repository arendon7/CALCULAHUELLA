from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .architecture import domain_architecture_summary
from .consolidation import build_consolidation_workbook, consolidation_summary, summary_json
from .database import add_audit, get_db
from .db.models import ConsolidationFinding, JourneyValidation, ReleaseGate

BASE_DIR = Path(__file__).resolve().parent


def register_consolidation_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash
) -> None:
    @app.get("/consolidacion", response_class=HTMLResponse)
    def consolidation_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "view_consolidation")
        summary = consolidation_summary(session, int(user["organization_id"]), BASE_DIR.parent)
        architecture = domain_architecture_summary(app, BASE_DIR.parent)
        return templates.TemplateResponse(
            request=request,
            name="consolidation.html",
            context=common_context(
                request,
                session,
                user,
                "consolidation",
                summary=summary,
                domain_architecture=architecture,
            ),
        )

    @app.post("/consolidacion/hallazgos/{finding_id}")
    def update_consolidation_finding(
        finding_id: int,
        request: Request,
        status: str = Form(...),
        owner: str = Form(""),
        target_version: str = Form("V1.0"),
        evidence: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_consolidation")
        finding = session.scalar(select(ConsolidationFinding).where(
            ConsolidationFinding.id == finding_id,
            ConsolidationFinding.organization_id == int(user["organization_id"]),
        ))
        if not finding:
            raise HTTPException(404, "Hallazgo no encontrado")
        if status not in {"Abierto", "En curso", "Bloqueado", "Resuelto", "Aceptado"}:
            raise HTTPException(400, "Estado inválido")
        previous = finding.status
        finding.status = status
        finding.owner = owner.strip() or finding.owner
        finding.target_version = target_version.strip() or finding.target_version
        finding.evidence = evidence.strip()
        add_audit(session, int(user["organization_id"]), str(user["email"]), "ACTUALIZAR", "Hallazgo de consolidación", finding.code, previous_value=previous, new_value=status, detail=finding.title)
        session.commit()
        set_flash(request, f"Hallazgo {finding.code} actualizado.")
        return RedirectResponse("/consolidacion#hallazgos", status_code=303)

    @app.post("/consolidacion/puertas/{gate_id}")
    def update_release_gate(
        gate_id: int,
        request: Request,
        status: str = Form(...),
        responsible: str = Form(""),
        evidence: str = Form(""),
        notes: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_consolidation")
        gate = session.scalar(select(ReleaseGate).where(
            ReleaseGate.id == gate_id,
            ReleaseGate.organization_id == int(user["organization_id"]),
        ))
        if not gate:
            raise HTTPException(404, "Puerta de salida no encontrada")
        if status not in {"Pendiente", "Parcial", "En revisión", "Aprobado", "Bloqueado"}:
            raise HTTPException(400, "Estado inválido")
        previous = gate.status
        gate.status = status
        gate.responsible = responsible.strip() or gate.responsible
        gate.evidence = evidence.strip()
        gate.notes = notes.strip()
        add_audit(session, int(user["organization_id"]), str(user["email"]), "ACTUALIZAR", "Puerta V1.0", gate.code, previous_value=previous, new_value=status, detail=gate.name)
        session.commit()
        set_flash(request, f"Puerta {gate.code} actualizada.")
        return RedirectResponse("/consolidacion#puertas", status_code=303)

    @app.post("/consolidacion/recorridos/{validation_id}")
    def update_journey_validation(
        validation_id: int,
        request: Request,
        status: str = Form(...),
        notes: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_consolidation")
        validation = session.scalar(select(JourneyValidation).where(
            JourneyValidation.id == validation_id,
            JourneyValidation.organization_id == int(user["organization_id"]),
        ))
        if not validation:
            raise HTTPException(404, "Recorrido no encontrado")
        if status not in {"No probado", "En prueba", "Con bloqueos", "Aprobado"}:
            raise HTTPException(400, "Estado inválido")
        previous = validation.status
        validation.status = status
        validation.notes = notes.strip()
        validation.tested_by = str(user["email"]) if status != "No probado" else ""
        validation.tested_at = datetime.now(UTC) if status != "No probado" else None
        add_audit(session, int(user["organization_id"]), str(user["email"]), "VALIDAR", "Recorrido por rol", validation.journey_code, previous_value=previous, new_value=status, detail=validation.notes)
        session.commit()
        set_flash(request, f"Recorrido {validation.journey_code} actualizado.")
        return RedirectResponse("/consolidacion#recorridos", status_code=303)

    @app.get("/consolidacion/exportar.xlsx")
    def export_consolidation(session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "view_consolidation")
        summary = consolidation_summary(session, int(user["organization_id"]), BASE_DIR.parent)
        content = build_consolidation_workbook(summary)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="consolidacion_v1_0.xlsx"'},
        )

    @app.get("/api/arquitectura/resumen")
    def architecture_api(user: dict = Depends(require_user)):
        ensure_capability(user, "view_consolidation")
        return domain_architecture_summary(app, BASE_DIR.parent)

    @app.get("/api/consolidacion/resumen")
    def consolidation_api(session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "view_consolidation")
        summary = consolidation_summary(session, int(user["organization_id"]), BASE_DIR.parent)
        return Response(content=summary_json(summary), media_type="application/json")
