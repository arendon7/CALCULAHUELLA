from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .database import add_audit, get_db
from .db.models import (
    ActivityData, EmissionCalculation, EmissionSource, Inventory, InventoryDecision,
    ReportArtifact, VerificationFinding,
)
from .storage import storage
from .verification import create_verification_package


def register_verification_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash,
    get_inventory, review_gate_summary
) -> None:
    @app.get("/verificacion", response_class=HTMLResponse)
    def verification_portal(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        if not (user["can_external_audit"] or user["can_review"] or user["can_approve"]):
            raise HTTPException(403, "Tu rol no tiene acceso al portal de verificación")
        inventory = get_inventory(session, user)
        gate = review_gate_summary(session, inventory)
        findings = list(session.scalars(
            select(VerificationFinding)
            .where(VerificationFinding.inventory_id == inventory.id)
            .options(selectinload(VerificationFinding.source))
            .order_by(VerificationFinding.status == "Cerrado", VerificationFinding.created_at.desc())
        ))
        reports = list(session.scalars(select(ReportArtifact).where(ReportArtifact.inventory_id == inventory.id).order_by(ReportArtifact.generated_at.desc())))
        decisions = list(session.scalars(select(InventoryDecision).where(InventoryDecision.inventory_id == inventory.id).order_by(InventoryDecision.decided_at.desc())))
        calculations_count = session.scalar(
            select(func.count()).select_from(EmissionCalculation).join(ActivityData).join(EmissionSource).where(EmissionSource.inventory_id == inventory.id)
        ) or 0
        evidence_with_files = sum(1 for item in inventory.documents if item.stored_name and storage.exists(item.stored_name))
        finding_counts = {
            "open": sum(1 for item in findings if item.status != "Cerrado"),
            "major": sum(1 for item in findings if item.status != "Cerrado" and item.severity in {"Mayor", "Crítica"}),
            "closed": sum(1 for item in findings if item.status == "Cerrado"),
        }
        return templates.TemplateResponse(
            request=request,
            name="verification.html",
            context=common_context(
                request, session, user, "verification", inventory=inventory, findings=findings, reports=reports,
                decisions=decisions, calculations_count=calculations_count, evidence_with_files=evidence_with_files,
                finding_counts=finding_counts, **gate,
            ),
        )

    @app.post("/verificacion/hallazgos/nuevo")
    def create_verification_finding(
        request: Request, inventory_id: int = Form(...), title: str = Form(...), description: str = Form(...),
        finding_type: str = Form("Observación"), severity: str = Form("Menor"), source_id: str = Form(""),
        session: Session = Depends(get_db), user: dict = Depends(require_user),
    ):
        ensure_capability(user, "external_audit")
        inventory = get_inventory(session, user, inventory_id)
        selected_source_id = int(source_id) if source_id.isdigit() else None
        if selected_source_id and not any(item.id == selected_source_id for item in inventory.sources):
            raise HTTPException(400, "La fuente no pertenece al inventario")
        finding = VerificationFinding(
            inventory_id=inventory.id, source_id=selected_source_id, title=title.strip(), description=description.strip(),
            finding_type=finding_type, severity=severity, status="Abierto", verifier_email=str(user["email"]),
        )
        session.add(finding)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "CREAR", "Hallazgo de verificación", finding.title, f"{finding_type} · {severity}")
        session.commit()
        set_flash(request, "Hallazgo registrado en el expediente de verificación.")
        return RedirectResponse("/verificacion", status_code=303)

    @app.post("/verificacion/hallazgos/{finding_id}/responder")
    def respond_verification_finding(
        finding_id: int, request: Request, management_response: str = Form(...),
        session: Session = Depends(get_db), user: dict = Depends(require_user),
    ):
        if not (user["can_manage_inventory"] or user["can_provide_data"] or user["can_review"]):
            raise HTTPException(403, "Tu rol no puede responder hallazgos")
        finding = session.scalar(
            select(VerificationFinding).join(Inventory).where(
                VerificationFinding.id == finding_id, Inventory.organization_id == int(user["organization_id"])
            )
        )
        if not finding:
            raise HTTPException(404, "Hallazgo no encontrado")
        finding.management_response = management_response.strip()
        finding.response_by = str(user["email"])
        finding.response_at = datetime.now(UTC)
        finding.status = "Respondido"
        add_audit(session, int(user["organization_id"]), str(user["email"]), "RESPONDER", "Hallazgo de verificación", finding.title, management_response[:180])
        session.commit()
        set_flash(request, "Respuesta enviada al verificador.")
        return RedirectResponse("/verificacion", status_code=303)

    @app.post("/verificacion/hallazgos/{finding_id}/cerrar")
    def close_verification_finding(
        finding_id: int, request: Request, conclusion: str = Form(...), decision: str = Form("Cerrar"),
        session: Session = Depends(get_db), user: dict = Depends(require_user),
    ):
        ensure_capability(user, "external_audit")
        finding = session.scalar(
            select(VerificationFinding).join(Inventory).where(
                VerificationFinding.id == finding_id, Inventory.organization_id == int(user["organization_id"])
            )
        )
        if not finding:
            raise HTTPException(404, "Hallazgo no encontrado")
        finding.conclusion = conclusion.strip()
        finding.closed_by = str(user["email"])
        if decision == "Cerrar":
            finding.status = "Cerrado"
            finding.closed_at = datetime.now(UTC)
        else:
            finding.status = "Abierto"
            finding.closed_at = None
        add_audit(session, int(user["organization_id"]), str(user["email"]), decision.upper(), "Hallazgo de verificación", finding.title, conclusion[:180])
        session.commit()
        set_flash(request, "Decisión del verificador registrada.")
        return RedirectResponse("/verificacion", status_code=303)

    @app.post("/verificacion/paquete")
    def generate_verification_package(
        request: Request, inventory_id: int = Form(...), session: Session = Depends(get_db), user: dict = Depends(require_user),
    ):
        if not (user["can_external_audit"] or user["can_review"] or user["can_approve"]):
            raise HTTPException(403, "Tu rol no puede generar el paquete de verificación")
        inventory = get_inventory(session, user, inventory_id)
        artifact = create_verification_package(session, inventory, str(user["email"]))
        add_audit(session, int(user["organization_id"]), str(user["email"]), "GENERAR", "Paquete de verificación", artifact.file_name, artifact.sha256)
        session.commit()
        set_flash(request, "Paquete de verificación generado con manifiesto, índices y archivos disponibles.")
        return RedirectResponse("/verificacion", status_code=303)
