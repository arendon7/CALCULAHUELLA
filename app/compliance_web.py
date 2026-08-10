from __future__ import annotations

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .database import add_audit, get_db
from .db.models import ComplianceAssessment, ComplianceRequirement, EvidenceDocument, Inventory


def compliance_score(rows: list[ComplianceAssessment]) -> int:
    applicable = [row for row in rows if row.status != "No aplica"]
    if not applicable:
        return 0
    weights = {"Cumple": 100, "Parcial": 50, "Pendiente": 0, "No cumple": 0}
    return round(sum(weights.get(row.status, 0) for row in applicable) / len(applicable))


def register_compliance_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash, get_inventory
) -> None:
    @app.get("/cumplimiento", response_class=HTMLResponse)
    def compliance_page(request: Request, inventory_id: int | None = None, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "view_compliance")
        inventory = get_inventory(session, user, inventory_id)
        rows = list(session.scalars(
            select(ComplianceAssessment)
            .where(ComplianceAssessment.inventory_id == inventory.id)
            .options(selectinload(ComplianceAssessment.requirement), selectinload(ComplianceAssessment.evidence))
            .join(ComplianceRequirement)
            .order_by(ComplianceRequirement.display_order)
        ))
        inventories = list(session.scalars(select(Inventory).where(Inventory.organization_id == int(user["organization_id"])).order_by(Inventory.start_date.desc())))
        score = compliance_score(rows)
        by_framework = {}
        for row in rows:
            by_framework.setdefault(row.requirement.framework, []).append(row)
        return templates.TemplateResponse(request=request, name="compliance.html", context=common_context(request, session, user, "compliance", inventory=inventory, inventories=inventories, rows=rows, by_framework=by_framework, compliance_score=score, documents=inventory.documents))

    @app.post("/cumplimiento/{assessment_id}/actualizar")
    def compliance_update(assessment_id: int, request: Request, status: str = Form(...), owner: str = Form("Responsable ambiental"), evidence_id: int | None = Form(None), notes: str = Form(""), session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_compliance")
        assessment = session.scalar(select(ComplianceAssessment).join(Inventory).where(ComplianceAssessment.id == assessment_id, Inventory.organization_id == int(user["organization_id"])).options(selectinload(ComplianceAssessment.requirement)))
        if not assessment:
            raise HTTPException(404, "Evaluación no encontrada")
        if status not in {"Cumple", "Parcial", "Pendiente", "No cumple", "No aplica"}:
            raise HTTPException(400, "Estado inválido")
        if evidence_id:
            evidence = session.scalar(select(EvidenceDocument).where(EvidenceDocument.id == evidence_id, EvidenceDocument.inventory_id == assessment.inventory_id))
            if not evidence:
                raise HTTPException(400, "La evidencia no pertenece al inventario")
        assessment.status = status
        assessment.owner = owner.strip()
        assessment.evidence_id = evidence_id or None
        assessment.notes = notes.strip()
        assessment.updated_by = str(user["email"])
        add_audit(session, int(user["organization_id"]), str(user["email"]), "EVALUAR", "Cumplimiento", assessment.requirement.code, f"Estado {status}")
        session.commit()
        set_flash(request, "Evaluación de cumplimiento actualizada.")
        return RedirectResponse(f"/cumplimiento?inventory_id={assessment.inventory_id}", status_code=303)
