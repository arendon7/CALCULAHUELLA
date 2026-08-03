from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .database import (
    AuditEvent, Inventory, InventoryDecision, ReviewObservation,
    add_audit, get_db,
)
from .notifications import notify_roles


def register_review_routes(
    app,
    templates,
    common_context,
    require_user,
    ensure_capability,
    set_flash,
    parse_date,
    get_inventory,
    get_source_for_user,
    ensure_inventory_editable,
    review_gate_summary,
    clone_inventory_version,
) -> None:
    @app.post("/control/observaciones/nueva")
    def observation_create(
        request: Request,
        inventory_id: int = Form(...),
        source_id: int | None = Form(None),
        entity_type: str = Form("Inventario"),
        entity_label: str = Form(""),
        title: str = Form(...),
        description: str = Form(...),
        severity: str = Form("Menor"),
        assigned_to: str = Form(""),
        due_date: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "review")
        inventory = get_inventory(session, user, inventory_id)
        ensure_inventory_editable(inventory)
        if severity not in {"Informativa", "Menor", "Mayor", "Crítica"}:
            raise HTTPException(400, "Severidad inválida")
        source = None
        if source_id:
            source = get_source_for_user(session, user, source_id)
            if source.inventory_id != inventory.id:
                raise HTTPException(400, "Fuente inválida")
        observation = ReviewObservation(
            inventory_id=inventory.id,
            source_id=source.id if source else None,
            entity_type=entity_type.strip() or "Inventario",
            entity_label=(source.name if source else entity_label.strip() or inventory.name),
            title=title.strip(),
            description=description.strip(),
            severity=severity,
            status="Abierta",
            assigned_to=assigned_to.strip(),
            due_date=parse_date(due_date) if due_date else None,
            created_by=str(user["email"]),
        )
        session.add(observation)
        notify_roles(session, int(user["organization_id"]), {"Cliente", "Consultor"}, f"Nueva observación · {severity}", observation.title, link="/control", category="Revisión", priority="Alta" if severity in {"Mayor", "Crítica"} else "Normal", email_requested=True)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "OBSERVAR", observation.entity_type, observation.entity_label, observation.title, new_value=severity)
        session.commit()
        set_flash(request, "La observación fue registrada y asignada.")
        return RedirectResponse("/control", status_code=303)
    @app.post("/control/observaciones/{observation_id}/responder")
    def observation_respond(
        observation_id: int,
        request: Request,
        response: str = Form(...),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        if not (user["can_provide_data"] or user["can_manage_sources"] or user["can_review"]):
            raise HTTPException(403, "Tu rol no puede responder observaciones")
        observation = session.scalar(
            select(ReviewObservation).join(Inventory).where(
                ReviewObservation.id == observation_id,
                Inventory.organization_id == int(user["organization_id"]),
            ).options(selectinload(ReviewObservation.inventory))
        )
        if not observation:
            raise HTTPException(404, "Observación no encontrada")
        ensure_inventory_editable(observation.inventory)
        if observation.status == "Cerrada":
            raise HTTPException(409, "La observación ya está cerrada")
        previous = observation.response
        observation.response = response.strip()
        observation.responded_by = str(user["email"])
        observation.responded_at = datetime.now(UTC)
        observation.status = "En corrección"
        add_audit(session, int(user["organization_id"]), str(user["email"]), "RESPONDER", "Observación", observation.title, "Respuesta del responsable", previous_value=previous, new_value=observation.response)
        session.commit()
        set_flash(request, "La respuesta fue registrada.")
        return RedirectResponse("/control", status_code=303)
    @app.post("/control/observaciones/{observation_id}/enviar")
    def observation_submit(
        observation_id: int,
        request: Request,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        if not (user["can_provide_data"] or user["can_manage_sources"]):
            raise HTTPException(403, "Tu rol no puede enviar correcciones")
        observation = session.scalar(
            select(ReviewObservation).join(Inventory).where(
                ReviewObservation.id == observation_id,
                Inventory.organization_id == int(user["organization_id"]),
            ).options(selectinload(ReviewObservation.inventory))
        )
        if not observation:
            raise HTTPException(404, "Observación no encontrada")
        ensure_inventory_editable(observation.inventory)
        if not observation.response.strip():
            raise HTTPException(400, "Primero registra una respuesta")
        observation.status = "Pendiente de cierre"
        add_audit(session, int(user["organization_id"]), str(user["email"]), "ENVIAR", "Observación", observation.title, "Corrección enviada al revisor")
        session.commit()
        set_flash(request, "La corrección fue enviada al revisor.")
        return RedirectResponse("/control", status_code=303)
    @app.post("/control/observaciones/{observation_id}/cerrar")
    def observation_close(
        observation_id: int,
        request: Request,
        resolution: str = Form(...),
        decision: str = Form("Cerrar"),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "review")
        observation = session.scalar(
            select(ReviewObservation).join(Inventory).where(
                ReviewObservation.id == observation_id,
                Inventory.organization_id == int(user["organization_id"]),
            ).options(selectinload(ReviewObservation.inventory))
        )
        if not observation:
            raise HTTPException(404, "Observación no encontrada")
        ensure_inventory_editable(observation.inventory)
        if decision == "Devolver":
            observation.status = "Devuelta"
            observation.resolution = resolution.strip()
            observation.resolved_by = str(user["email"])
            observation.resolved_at = datetime.now(UTC)
            action = "DEVOLVER"
            message = "La observación fue devuelta para corrección."
        else:
            observation.status = "Cerrada"
            observation.resolution = resolution.strip()
            observation.resolved_by = str(user["email"])
            observation.resolved_at = datetime.now(UTC)
            observation.closed_by = str(user["email"])
            observation.closed_at = datetime.now(UTC)
            action = "CERRAR"
            message = "La observación fue cerrada."
        add_audit(session, int(user["organization_id"]), str(user["email"]), action, "Observación", observation.title, observation.resolution)
        session.commit()
        set_flash(request, message)
        return RedirectResponse("/control", status_code=303)
    @app.post("/control/inventario/enviar-revision")
    def inventory_submit_review(
        request: Request,
        inventory_id: int = Form(...),
        comments: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_inventory")
        inventory = get_inventory(session, user, inventory_id)
        ensure_inventory_editable(inventory)
        inventory.status = "En revisión"
        inventory.current_stage = "Revisión"
        inventory.submitted_for_review_at = datetime.now(UTC)
        inventory.submitted_for_review_by = str(user["email"])
        session.add(InventoryDecision(inventory_id=inventory.id, decision_type="Envío a revisión", decision="Enviado", comments=comments.strip(), decided_by=str(user["email"]), inventory_version=inventory.version))
        notify_roles(session, int(user["organization_id"]), {"Revisor"}, "Inventario enviado a revisión", inventory.name, link="/control", category="Flujo", priority="Alta", email_requested=True)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "ENVIAR", "Inventario", inventory.name, "Inventario enviado a revisión profesional", reason=comments.strip())
        session.commit()
        set_flash(request, "El inventario fue enviado a revisión profesional.")
        return RedirectResponse("/control", status_code=303)
    @app.post("/control/inventario/recomendar")
    def inventory_recommend(
        request: Request,
        inventory_id: int = Form(...),
        comments: str = Form(...),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "review")
        inventory = get_inventory(session, user, inventory_id)
        ensure_inventory_editable(inventory)
        gates = review_gate_summary(session, inventory)
        if not gates["can_approve"]:
            raise HTTPException(409, "No puede recomendarse la aprobación mientras existan bloqueos de calidad")
        inventory.status = "Pendiente de aprobación"
        inventory.current_stage = "Aprobación"
        session.add(InventoryDecision(inventory_id=inventory.id, decision_type="Revisión técnica", decision="Recomendada", comments=comments.strip(), decided_by=str(user["email"]), inventory_version=inventory.version))
        add_audit(session, int(user["organization_id"]), str(user["email"]), "RECOMENDAR", "Inventario", inventory.name, "Revisión técnica favorable", reason=comments.strip())
        session.commit()
        set_flash(request, "La aprobación fue recomendada. Debe decidir un usuario diferente.")
        return RedirectResponse("/control", status_code=303)
    @app.post("/control/inventario/aprobar")
    def inventory_approve(
        request: Request,
        inventory_id: int = Form(...),
        comments: str = Form(...),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "approve")
        inventory = get_inventory(session, user, inventory_id)
        ensure_inventory_editable(inventory)
        gates = review_gate_summary(session, inventory)
        if not gates["can_approve"]:
            raise HTTPException(409, "El inventario no cumple todas las puertas de calidad")
        recommendation = session.scalar(select(InventoryDecision).where(
            InventoryDecision.inventory_id == inventory.id,
            InventoryDecision.decision_type == "Revisión técnica",
            InventoryDecision.decision == "Recomendada",
        ).order_by(InventoryDecision.decided_at.desc()))
        if not recommendation:
            raise HTTPException(409, "Primero se requiere una recomendación de revisión técnica")
        if recommendation.decided_by == str(user["email"]):
            raise HTTPException(409, "La aprobación final debe realizarla una persona diferente del revisor que recomendó")
        inventory.status = "Aprobado"
        inventory.current_stage = "Aprobación"
        inventory.approved_at = datetime.now(UTC)
        inventory.approved_by = str(user["email"])
        session.add(InventoryDecision(inventory_id=inventory.id, decision_type="Aprobación final", decision="Aprobado", comments=comments.strip(), decided_by=str(user["email"]), inventory_version=inventory.version))
        notify_roles(session, int(user["organization_id"]), {"Administrador", "Consultor", "Cliente"}, "Inventario aprobado", f"{inventory.name} fue aprobado por {user['name']}.", link="/reportes", category="Aprobación", priority="Alta", email_requested=True)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "APROBAR", "Inventario", inventory.name, "Aprobación final registrada", reason=comments.strip())
        session.commit()
        set_flash(request, "El inventario fue aprobado. Ahora puede cerrarse y quedar inmutable.")
        return RedirectResponse("/control", status_code=303)
    @app.post("/control/inventario/cerrar")
    def inventory_close(
        request: Request,
        inventory_id: int = Form(...),
        comments: str = Form(...),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "approve")
        inventory = get_inventory(session, user, inventory_id)
        ensure_inventory_editable(inventory)
        if inventory.status != "Aprobado":
            raise HTTPException(409, "Solo puede cerrarse un inventario aprobado")
        inventory.status = "Cerrado"
        inventory.current_stage = "Informe"
        inventory.locked = True
        inventory.closed_at = datetime.now(UTC)
        inventory.closed_by = str(user["email"])
        session.add(InventoryDecision(inventory_id=inventory.id, decision_type="Cierre", decision="Cerrado", comments=comments.strip(), decided_by=str(user["email"]), inventory_version=inventory.version))
        add_audit(session, int(user["organization_id"]), str(user["email"]), "CERRAR", "Inventario", inventory.name, "Inventario bloqueado e inmutable", reason=comments.strip())
        session.commit()
        set_flash(request, "El inventario quedó cerrado e inmutable.")
        return RedirectResponse("/control", status_code=303)
    @app.post("/control/inventario/reabrir")
    def inventory_reopen(
        request: Request,
        inventory_id: int = Form(...),
        reason: str = Form(...),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_org")
        inventory = get_inventory(session, user, inventory_id)
        if not inventory.locked or inventory.status != "Cerrado":
            raise HTTPException(409, "Solo puede generarse una nueva versión desde un inventario cerrado")
        new_inventory = clone_inventory_version(session, inventory, user, reason.strip())
        session.add(InventoryDecision(inventory_id=inventory.id, decision_type="Reapertura", decision="Nueva versión", comments=reason.strip(), decided_by=str(user["email"]), inventory_version=inventory.version))
        add_audit(session, int(user["organization_id"]), str(user["email"]), "REABRIR", "Inventario", inventory.name, f"Nueva versión #{new_inventory.id} · {new_inventory.version}", reason=reason.strip())
        session.commit()
        set_flash(request, f"Se creó la nueva versión {new_inventory.version}; el inventario original permanece inmutable.")
        return RedirectResponse(f"/inventarios/{new_inventory.id}", status_code=303)
    @app.get("/control", response_class=HTMLResponse)
    def control_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        inventory = get_inventory(session, user)
        observations = list(
            session.scalars(
                select(ReviewObservation)
                .where(ReviewObservation.inventory_id == inventory.id)
                .options(selectinload(ReviewObservation.source))
                .order_by(
                    ReviewObservation.status == "Cerrada",
                    ReviewObservation.created_at.desc(),
                )
            )
        )
        decisions = list(
            session.scalars(
                select(InventoryDecision)
                .where(InventoryDecision.inventory_id == inventory.id)
                .order_by(InventoryDecision.decided_at.desc())
            )
        )
        events = list(
            session.scalars(
                select(AuditEvent)
                .where(AuditEvent.organization_id == int(user["organization_id"]))
                .order_by(AuditEvent.created_at.desc())
                .limit(40)
            )
        )
        summary = review_gate_summary(session, inventory)
        latest_recommendation = session.scalar(
            select(InventoryDecision)
            .where(
                InventoryDecision.inventory_id == inventory.id,
                InventoryDecision.decision_type == "Revisión técnica",
                InventoryDecision.decision == "Recomendada",
            )
            .order_by(InventoryDecision.decided_at.desc())
        )
        observation_counts = {
            "open": sum(1 for item in observations if item.status != "Cerrada"),
            "blocking": sum(1 for item in observations if item.status != "Cerrada" and item.severity in {"Mayor", "Crítica"}),
            "closed": sum(1 for item in observations if item.status == "Cerrada"),
        }
        return templates.TemplateResponse(
            request=request,
            name="control.html",
            context=common_context(
                request,
                session,
                user,
                "control",
                inventory=inventory,
                events=events,
                observations=observations,
                decisions=decisions,
                observation_counts=observation_counts,
                latest_recommendation=latest_recommendation,
                **summary,
            ),
        )
