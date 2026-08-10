from __future__ import annotations

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .database import add_audit, get_db
from .db.models import Organization, OrganizationMembership
from .product_experience import demo_story_for


def register_portfolio_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash
) -> None:
    @app.get("/portafolio", response_class=HTMLResponse)
    def portfolio_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_portfolio")
        memberships = list(session.scalars(
            select(OrganizationMembership)
            .where(OrganizationMembership.user_id == int(user["id"]), OrganizationMembership.active.is_(True))
            .options(selectinload(OrganizationMembership.organization).selectinload(Organization.inventories))
            .order_by(OrganizationMembership.id)
        ))
        portfolio = []
        for membership in memberships:
            org_item = membership.organization
            inventories = org_item.inventories if org_item else []
            portfolio.append({
                "membership": membership,
                "organization": org_item,
                "inventories": inventories,
                "latest_inventory": sorted(inventories, key=lambda item: (item.start_date, item.id), reverse=True)[0] if inventories else None,
                "demo_story": demo_story_for(org_item.trade_name) if org_item else None,
            })
        return templates.TemplateResponse(
            request=request,
            name="portfolio.html",
            context=common_context(request, session, user, "portfolio", portfolio=portfolio),
        )

    @app.post("/portafolio/cambiar/{organization_id}")
    def portfolio_switch(organization_id: int, request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        membership = session.scalar(select(OrganizationMembership).where(
            OrganizationMembership.user_id == int(user["id"]),
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.active.is_(True),
        ))
        if not membership:
            raise HTTPException(403, "No tienes acceso a esta organización")
        request.session["active_org_id"] = organization_id
        add_audit(session, organization_id, str(user["email"]), "CAMBIAR", "Organización activa", str(organization_id), "Cambio de contexto multiempresa")
        session.commit()
        set_flash(request, "Organización activa actualizada.")
        return RedirectResponse("/dashboard", status_code=303)

    @app.post("/portafolio/nueva")
    def portfolio_create(
        request: Request,
        name: str = Form(...),
        trade_name: str = Form(""),
        tax_id: str = Form(...),
        sector: str = Form(...),
        city: str = Form("Medellín"),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_org")
        if session.scalar(select(Organization).where(func.lower(Organization.name) == name.strip().lower())):
            raise HTTPException(409, "Ya existe una organización con ese nombre")
        organization = Organization(
            name=name.strip(), trade_name=trade_name.strip() or name.strip(), tax_id=tax_id.strip(),
            sector=sector.strip(), country="Colombia", department="Antioquia", city=city.strip(),
            contact_name=str(user["name"]), contact_email=str(user["email"]), status="Activa",
        )
        session.add(organization)
        session.flush()
        session.add(OrganizationMembership(
            user_id=int(user["id"]), organization_id=organization.id, role="Administrador", active=True,
        ))
        add_audit(session, organization.id, str(user["email"]), "CREAR", "Organización", organization.name, "Alta desde portafolio multiempresa")
        session.commit()
        request.session["active_org_id"] = organization.id
        set_flash(request, "Organización creada. Ahora puedes configurar sedes e inventarios.")
        return RedirectResponse("/organizacion", status_code=303)
