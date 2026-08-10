from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .customer_success import account_metrics, refresh_account_health, sync_renewal_opportunity
from .database import add_audit, get_db
from .db.models import (
    AccountHealthSnapshot,
    CustomerSuccessProfile,
    Inventory,
    RenewalOpportunity,
    SuccessCommitment,
    ValueMilestone,
)


def _require_customer_success_view(user: dict[str, object]) -> None:
    capabilities = user.get("capabilities", set())
    if "view_customer_success" not in capabilities and "manage_customer_success" not in capabilities:
        raise HTTPException(403, "Tu rol no tiene acceso a éxito del cliente")


def register_customer_success_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash, parse_date
) -> None:
    @app.get("/exito-cliente", response_class=HTMLResponse)
    def customer_success_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        _require_customer_success_view(user)
        organization_id = int(user["organization_id"])
        profile = session.scalar(select(CustomerSuccessProfile).where(CustomerSuccessProfile.organization_id == organization_id))
        snapshot = session.scalar(
            select(AccountHealthSnapshot)
            .where(AccountHealthSnapshot.organization_id == organization_id)
            .order_by(AccountHealthSnapshot.calculated_at.desc())
        )
        if not snapshot:
            snapshot = refresh_account_health(session, organization_id, str(user["email"]))
            sync_renewal_opportunity(session, organization_id, snapshot, str(user["email"]))
            session.commit()
        metrics = account_metrics(session, organization_id)
        milestones = list(session.scalars(
            select(ValueMilestone)
            .where(ValueMilestone.organization_id == organization_id)
            .options(selectinload(ValueMilestone.inventory))
            .order_by(ValueMilestone.target_date, ValueMilestone.id)
        ))
        commitments = list(session.scalars(
            select(SuccessCommitment)
            .where(SuccessCommitment.organization_id == organization_id)
            .order_by(SuccessCommitment.status, SuccessCommitment.due_date, SuccessCommitment.id)
        ))
        renewal = session.scalar(
            select(RenewalOpportunity)
            .where(RenewalOpportunity.organization_id == organization_id)
            .options(selectinload(RenewalOpportunity.contract))
            .order_by(RenewalOpportunity.renewal_date)
        )
        history = list(session.scalars(
            select(AccountHealthSnapshot)
            .where(AccountHealthSnapshot.organization_id == organization_id)
            .order_by(AccountHealthSnapshot.calculated_at.desc())
            .limit(8)
        ))
        inventories = list(session.scalars(
            select(Inventory).where(Inventory.organization_id == organization_id).order_by(Inventory.start_date.desc())
        ))
        portfolio = []
        if user.get("can_manage_customer_success"):
            for item in user.get("organizations", []):
                org_id = int(item["id"])
                latest = session.scalar(
                    select(AccountHealthSnapshot)
                    .where(AccountHealthSnapshot.organization_id == org_id)
                    .order_by(AccountHealthSnapshot.calculated_at.desc())
                )
                if latest:
                    portfolio.append({"organization": item, "snapshot": latest})
        return templates.TemplateResponse(
            request=request,
            name="customer_success.html",
            context=common_context(
                request, session, user, "customer_success",
                profile=profile, snapshot=snapshot, metrics=metrics, milestones=milestones,
                commitments=commitments, renewal=renewal, history=history, inventories=inventories,
                portfolio=portfolio,
            ),
        )

    @app.post("/exito-cliente/perfil")
    def customer_success_profile_update(
        request: Request,
        lifecycle_stage: str = Form("Adopción"), owner: str = Form("Equipo de éxito del cliente"),
        executive_sponsor: str = Form(""), sponsor_email: str = Form(""),
        primary_objective: str = Form(""), success_plan: str = Form(""),
        risk_override: str = Form(""), risk_reason: str = Form(""),
        last_business_review: str = Form(""), next_business_review: str = Form(""),
        satisfaction_score: str = Form(""), nps_score: str = Form(""),
        session: Session = Depends(get_db), user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_customer_success")
        organization_id = int(user["organization_id"])
        profile = session.scalar(select(CustomerSuccessProfile).where(CustomerSuccessProfile.organization_id == organization_id))
        if not profile:
            profile = CustomerSuccessProfile(organization_id=organization_id)
            session.add(profile)
        allowed_stages = {"Implementación", "Adopción", "Valor", "Renovación", "Expansión", "En riesgo"}
        allowed_risks = {"", "Sano", "Atención", "Riesgo", "Crítico"}
        if lifecycle_stage not in allowed_stages or risk_override not in allowed_risks:
            raise HTTPException(400, "Etapa o nivel de riesgo inválido")
        profile.lifecycle_stage = lifecycle_stage
        profile.owner = owner.strip() or "Equipo de éxito del cliente"
        profile.executive_sponsor = executive_sponsor.strip()
        profile.sponsor_email = sponsor_email.strip().lower()
        profile.primary_objective = primary_objective.strip()
        profile.success_plan = success_plan.strip()
        profile.risk_override = risk_override
        profile.risk_reason = risk_reason.strip()
        profile.last_business_review = parse_date(last_business_review) if last_business_review else None
        profile.next_business_review = parse_date(next_business_review) if next_business_review else None
        profile.satisfaction_score = float(satisfaction_score) if satisfaction_score else None
        profile.nps_score = int(nps_score) if nps_score else None
        if profile.satisfaction_score is not None and not 1 <= profile.satisfaction_score <= 5:
            raise HTTPException(400, "La satisfacción debe estar entre 1 y 5")
        if profile.nps_score is not None and not 0 <= profile.nps_score <= 10:
            raise HTTPException(400, "El NPS relacional debe estar entre 0 y 10")
        add_audit(session, organization_id, str(user["email"]), "ACTUALIZAR", "Éxito del cliente", "Perfil de cuenta", new_value=lifecycle_stage)
        session.commit()
        set_flash(request, "Perfil de éxito del cliente actualizado.")
        return RedirectResponse("/exito-cliente", status_code=303)

    @app.post("/exito-cliente/salud/recalcular")
    def customer_success_recalculate(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_customer_success")
        organization_id = int(user["organization_id"])
        snapshot = refresh_account_health(session, organization_id, str(user["email"]))
        renewal = sync_renewal_opportunity(session, organization_id, snapshot, str(user["email"]))
        add_audit(
            session, organization_id, str(user["email"]), "RECALCULAR", "Salud de cuenta", str(snapshot.id),
            new_value=f"{snapshot.overall_score} · {snapshot.risk_level}",
            detail=f"Renovación: {renewal.probability}%" if renewal else "Sin contrato vigente",
        )
        session.commit()
        set_flash(request, f"Salud recalculada: {snapshot.overall_score}/100 · {snapshot.risk_level}.")
        return RedirectResponse("/exito-cliente", status_code=303)

    @app.post("/exito-cliente/hitos/nuevo")
    def customer_success_milestone_create(
        request: Request, title: str = Form(...), category: str = Form("Resultado climático"),
        inventory_id: str = Form(""), owner: str = Form("Equipo de éxito del cliente"),
        target_date: str = Form(""), expected_value: float = Form(0), realized_value: float = Form(0),
        unit: str = Form(""), status: str = Form("Planeado"), evidence_note: str = Form(""),
        session: Session = Depends(get_db), user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_customer_success")
        organization_id = int(user["organization_id"])
        inventory = session.get(Inventory, int(inventory_id)) if inventory_id.strip().isdigit() else None
        if inventory and inventory.organization_id != organization_id:
            raise HTTPException(409, "El inventario no corresponde a la organización activa")
        allowed = {"Planeado", "En progreso", "Completado", "Cancelado"}
        if status not in allowed:
            raise HTTPException(400, "Estado de hito inválido")
        milestone = ValueMilestone(
            organization_id=organization_id, inventory_id=inventory.id if inventory else None,
            title=title.strip(), category=category.strip() or "Resultado climático", owner=owner.strip(),
            target_date=parse_date(target_date) if target_date else None,
            expected_value=max(0, expected_value), realized_value=max(0, realized_value), unit=unit.strip(),
            status=status, evidence_note=evidence_note.strip(), created_by=str(user["email"]),
            completed_at=datetime.now(UTC) if status == "Completado" else None,
        )
        session.add(milestone)
        add_audit(session, organization_id, str(user["email"]), "CREAR", "Hito de valor", milestone.title, new_value=status)
        session.commit()
        set_flash(request, "Hito de valor creado.")
        return RedirectResponse("/exito-cliente", status_code=303)

    @app.post("/exito-cliente/hitos/{milestone_id}/estado")
    def customer_success_milestone_update(
        milestone_id: int, request: Request, status: str = Form(...), realized_value: float = Form(0),
        evidence_note: str = Form(""), session: Session = Depends(get_db), user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_customer_success")
        milestone = session.get(ValueMilestone, milestone_id)
        if not milestone or milestone.organization_id != int(user["organization_id"]):
            raise HTTPException(404, "Hito no encontrado")
        allowed = {"Planeado", "En progreso", "Completado", "Cancelado"}
        if status not in allowed:
            raise HTTPException(400, "Estado de hito inválido")
        previous = milestone.status
        milestone.status = status
        milestone.realized_value = max(0, realized_value)
        milestone.evidence_note = evidence_note.strip() or milestone.evidence_note
        milestone.completed_at = datetime.now(UTC) if status == "Completado" else None
        add_audit(session, milestone.organization_id, str(user["email"]), "ACTUALIZAR", "Hito de valor", milestone.title, previous_value=previous, new_value=status)
        session.commit()
        set_flash(request, "Hito actualizado.")
        return RedirectResponse("/exito-cliente", status_code=303)

    @app.post("/exito-cliente/compromisos/nuevo")
    def customer_success_commitment_create(
        request: Request, title: str = Form(...), description: str = Form(""), owner: str = Form(""),
        due_date: str = Form(""), priority: str = Form("Media"), source: str = Form("Plan de éxito"),
        session: Session = Depends(get_db), user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_customer_success")
        organization_id = int(user["organization_id"])
        commitment = SuccessCommitment(
            organization_id=organization_id, title=title.strip(), description=description.strip(),
            owner=owner.strip() or "Equipo de éxito del cliente", due_date=parse_date(due_date) if due_date else None,
            priority=priority if priority in {"Baja", "Media", "Alta", "Crítica"} else "Media",
            status="Pendiente", source=source.strip() or "Plan de éxito", created_by=str(user["email"]),
        )
        session.add(commitment)
        add_audit(session, organization_id, str(user["email"]), "CREAR", "Compromiso de éxito", commitment.title, new_value=commitment.priority)
        session.commit()
        set_flash(request, "Compromiso creado.")
        return RedirectResponse("/exito-cliente", status_code=303)

    @app.post("/exito-cliente/compromisos/{commitment_id}/estado")
    def customer_success_commitment_update(
        commitment_id: int, request: Request, status: str = Form(...),
        session: Session = Depends(get_db), user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_customer_success")
        commitment = session.get(SuccessCommitment, commitment_id)
        if not commitment or commitment.organization_id != int(user["organization_id"]):
            raise HTTPException(404, "Compromiso no encontrado")
        allowed = {"Pendiente", "En progreso", "Completado", "Bloqueado", "Cancelado"}
        if status not in allowed:
            raise HTTPException(400, "Estado de compromiso inválido")
        previous = commitment.status
        commitment.status = status
        commitment.completed_at = datetime.now(UTC) if status == "Completado" else None
        add_audit(session, commitment.organization_id, str(user["email"]), "ACTUALIZAR", "Compromiso de éxito", commitment.title, previous_value=previous, new_value=status)
        session.commit()
        set_flash(request, "Compromiso actualizado.")
        return RedirectResponse("/exito-cliente", status_code=303)

    @app.post("/exito-cliente/renovacion/{renewal_id}/actualizar")
    def customer_success_renewal_update(
        renewal_id: int, request: Request, status: str = Form(...), probability: int = Form(...),
        strategy: str = Form(""), blockers: str = Form(""), next_action: str = Form(""),
        next_action_date: str = Form(""), decision_notes: str = Form(""),
        session: Session = Depends(get_db), user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_customer_success")
        renewal = session.get(RenewalOpportunity, renewal_id)
        if not renewal or renewal.organization_id != int(user["organization_id"]):
            raise HTTPException(404, "Oportunidad de renovación no encontrada")
        allowed = {"Por preparar", "Bien encaminada", "En riesgo", "Propuesta enviada", "Renovada", "No renovada"}
        if status not in allowed or not 0 <= probability <= 100:
            raise HTTPException(400, "Estado o probabilidad inválidos")
        previous = f"{renewal.status} · {renewal.probability}%"
        renewal.status = status
        renewal.probability = probability
        renewal.strategy = strategy.strip()
        renewal.blockers = blockers.strip()
        renewal.next_action = next_action.strip()
        renewal.next_action_date = parse_date(next_action_date) if next_action_date else None
        renewal.decision_notes = decision_notes.strip()
        renewal.updated_by = str(user["email"])
        add_audit(session, renewal.organization_id, str(user["email"]), "ACTUALIZAR", "Renovación", str(renewal.id), previous_value=previous, new_value=f"{status} · {probability}%")
        session.commit()
        set_flash(request, "Estrategia de renovación actualizada.")
        return RedirectResponse("/exito-cliente", status_code=303)
