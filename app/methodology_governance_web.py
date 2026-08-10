from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .database import add_audit, get_db
from .db.models import Inventory, InventoryMethodologySnapshot, MethodologyRelease


def register_methodology_governance_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash, parse_date, get_inventory
) -> None:
    @app.get("/gobierno-metodologico", response_class=HTMLResponse)
    def methodology_governance_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_methodology_governance")
        releases = list(session.scalars(select(MethodologyRelease).where(MethodologyRelease.organization_id == int(user["organization_id"])).order_by(MethodologyRelease.created_at.desc())))
        inventories = list(session.scalars(select(Inventory).where(Inventory.organization_id == int(user["organization_id"])).order_by(Inventory.start_date.desc())))
        snapshots = list(session.scalars(select(InventoryMethodologySnapshot).join(Inventory).where(Inventory.organization_id == int(user["organization_id"])).options(selectinload(InventoryMethodologySnapshot.inventory), selectinload(InventoryMethodologySnapshot.release)).order_by(InventoryMethodologySnapshot.created_at.desc())))
        return templates.TemplateResponse(request=request, name="methodology_governance.html", context=common_context(request, session, user, "methodology_governance", releases=releases, inventories=inventories, snapshots=snapshots))

    @app.post("/gobierno-metodologico/versiones/nueva")
    def methodology_release_create(request: Request, name: str = Form(...), version: str = Form(...), issuing_body: str = Form("Calcula tu Huella"), publication_date: str = Form(""), effective_from: str = Form(""), source_reference: str = Form(""), notes: str = Form(""), session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_methodology_governance")
        if session.scalar(select(MethodologyRelease).where(MethodologyRelease.organization_id == int(user["organization_id"]), MethodologyRelease.name == name.strip(), MethodologyRelease.version == version.strip())):
            raise HTTPException(409, "La versión metodológica ya existe")
        fingerprint = hashlib.sha256(f"{name}|{version}|{source_reference}|{notes}".encode()).hexdigest()
        release = MethodologyRelease(organization_id=int(user["organization_id"]), name=name.strip(), version=version.strip(), issuing_body=issuing_body.strip(), publication_date=parse_date(publication_date) if publication_date else None, effective_from=parse_date(effective_from) if effective_from else None, status="Borrador", source_reference=source_reference.strip(), content_hash=fingerprint, notes=notes.strip())
        session.add(release)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "CREAR", "Versión metodológica", f"{release.name} {release.version}", fingerprint)
        session.commit()
        set_flash(request, "Versión metodológica creada en borrador.")
        return RedirectResponse("/gobierno-metodologico", status_code=303)

    @app.post("/gobierno-metodologico/versiones/{release_id}/aprobar")
    def methodology_release_approve(release_id: int, request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_methodology_governance")
        release = session.scalar(select(MethodologyRelease).where(MethodologyRelease.id == release_id, MethodologyRelease.organization_id == int(user["organization_id"])))
        if not release:
            raise HTTPException(404, "Versión no encontrada")
        release.status = "Aprobado"
        release.approved_by = str(user["email"])
        release.approved_at = datetime.now(UTC)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "APROBAR", "Versión metodológica", f"{release.name} {release.version}")
        session.commit()
        set_flash(request, "Versión metodológica aprobada.")
        return RedirectResponse("/gobierno-metodologico", status_code=303)

    @app.post("/gobierno-metodologico/snapshots/nuevo")
    def methodology_snapshot_create(request: Request, inventory_id: int = Form(...), methodology_release_id: int | None = Form(None), snapshot_name: str = Form(...), policy_notes: str = Form(""), session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_methodology_governance")
        inventory = get_inventory(session, user, inventory_id)
        release = None
        if methodology_release_id:
            release = session.scalar(select(MethodologyRelease).where(MethodologyRelease.id == methodology_release_id, MethodologyRelease.organization_id == int(user["organization_id"])))
            if not release:
                raise HTTPException(400, "Versión metodológica inválida")
        snapshot = InventoryMethodologySnapshot(inventory_id=inventory.id, methodology_release_id=release.id if release else None, snapshot_name=snapshot_name.strip(), status="Aprobado", methodology_name=inventory.methodology, methodology_version=inventory.methodology_version, gwp_version=inventory.gwp_version, consolidation_approach=inventory.consolidation_approach, materiality_threshold=inventory.materiality_threshold, policy_json=json.dumps({"notes": policy_notes.strip(), "inventory_version": inventory.version}, ensure_ascii=False), approved_by=str(user["email"]), approved_at=datetime.now(UTC))
        session.add(snapshot)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "CONGELAR", "Snapshot metodológico", snapshot.snapshot_name, f"Inventario #{inventory.id}")
        session.commit()
        set_flash(request, "Configuración metodológica congelada para el inventario.")
        return RedirectResponse("/gobierno-metodologico", status_code=303)
