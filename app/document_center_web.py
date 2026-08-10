from __future__ import annotations

from datetime import date

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .database import add_audit, get_db
from .db.models import DocumentControlRecord, EvidenceDocument, Inventory, ReportArtifact


def register_document_center_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash, parse_date, get_inventory
) -> None:
    @app.get("/centro-documental", response_class=HTMLResponse)
    def document_center_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_documents")
        records = list(session.scalars(select(DocumentControlRecord).where(DocumentControlRecord.organization_id == int(user["organization_id"])).options(selectinload(DocumentControlRecord.inventory), selectinload(DocumentControlRecord.evidence), selectinload(DocumentControlRecord.report)).order_by(DocumentControlRecord.category, DocumentControlRecord.document_code)))
        inventories = list(session.scalars(select(Inventory).where(Inventory.organization_id == int(user["organization_id"])).order_by(Inventory.start_date.desc())))
        evidence = list(session.scalars(select(EvidenceDocument).join(Inventory).where(Inventory.organization_id == int(user["organization_id"])).order_by(EvidenceDocument.uploaded_at.desc()).limit(100)))
        reports = list(session.scalars(select(ReportArtifact).join(Inventory).where(Inventory.organization_id == int(user["organization_id"])).order_by(ReportArtifact.generated_at.desc()).limit(100)))
        due = [row for row in records if row.review_due and row.review_due <= date.today()]
        return templates.TemplateResponse(request=request, name="document_center.html", context=common_context(request, session, user, "documents", records=records, inventories=inventories, evidence=evidence, reports=reports, due=due))

    @app.post("/centro-documental/registros/nuevo")
    def document_record_create(request: Request, document_code: str = Form(...), title: str = Form(...), category: str = Form("Soporte"), version: str = Form("1.0"), owner: str = Form("Gestión ambiental"), confidentiality: str = Form("Interno"), retention_years: int = Form(7), review_due: str = Form(""), inventory_id: int | None = Form(None), evidence_document_id: int | None = Form(None), report_artifact_id: int | None = Form(None), notes: str = Form(""), session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_documents")
        organization_id = int(user["organization_id"])
        if session.scalar(select(DocumentControlRecord).where(DocumentControlRecord.organization_id == organization_id, DocumentControlRecord.document_code == document_code.strip())):
            raise HTTPException(409, "El código documental ya existe")
        inventory = get_inventory(session, user, inventory_id) if inventory_id else None
        evidence = None
        report = None
        if evidence_document_id:
            evidence = session.scalar(select(EvidenceDocument).join(Inventory).where(EvidenceDocument.id == evidence_document_id, Inventory.organization_id == organization_id))
            if not evidence:
                raise HTTPException(400, "Evidencia inválida")
        if report_artifact_id:
            report = session.scalar(select(ReportArtifact).join(Inventory).where(ReportArtifact.id == report_artifact_id, Inventory.organization_id == organization_id))
            if not report:
                raise HTTPException(400, "Informe inválido")
        row = DocumentControlRecord(organization_id=organization_id, inventory_id=inventory.id if inventory else None, evidence_document_id=evidence.id if evidence else None, report_artifact_id=report.id if report else None, document_code=document_code.strip(), title=title.strip(), category=category.strip(), version=version.strip(), owner=owner.strip(), confidentiality=confidentiality, retention_years=max(1, retention_years), review_due=parse_date(review_due) if review_due else None, status="Vigente", sha256=(evidence.sha256 if evidence else (report.sha256 if report else "")), notes=notes.strip(), created_by=str(user["email"]))
        session.add(row)
        add_audit(session, organization_id, str(user["email"]), "REGISTRAR", "Documento controlado", row.document_code, row.title)
        session.commit()
        set_flash(request, "Documento incorporado al registro maestro.")
        return RedirectResponse("/centro-documental", status_code=303)

    @app.post("/centro-documental/registros/{record_id}/actualizar")
    def document_record_update(record_id: int, request: Request, status: str = Form(...), version: str = Form(...), owner: str = Form(...), confidentiality: str = Form(...), review_due: str = Form(""), notes: str = Form(""), session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_documents")
        row = session.scalar(select(DocumentControlRecord).where(DocumentControlRecord.id == record_id, DocumentControlRecord.organization_id == int(user["organization_id"])))
        if not row:
            raise HTTPException(404, "Documento no encontrado")
        row.status = status
        row.version = version.strip()
        row.owner = owner.strip()
        row.confidentiality = confidentiality
        row.review_due = parse_date(review_due) if review_due else None
        row.notes = notes.strip()
        add_audit(session, int(user["organization_id"]), str(user["email"]), "ACTUALIZAR", "Documento controlado", row.document_code, f"Versión {row.version} · {row.status}")
        session.commit()
        set_flash(request, "Control documental actualizado.")
        return RedirectResponse("/centro-documental", status_code=303)
