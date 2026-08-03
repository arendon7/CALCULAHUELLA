from __future__ import annotations

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from .database import get_db
from .repositories.organizations import get_organization
from .services.organizations import create_facility, update_facility, update_organization


def register_organization_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash
) -> None:
    @app.get("/organizacion", response_class=HTMLResponse)
    def organization_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        org = get_organization(session, int(user["organization_id"]), include_graph=True)
        return templates.TemplateResponse(
            request=request,
            name="organization.html",
            context=common_context(request, session, user, "organization", organization=org),
        )
    @app.post("/organizacion/editar")
    def organization_edit(
        request: Request,
        name: str = Form(...),
        trade_name: str = Form(""),
        tax_id: str = Form(...),
        sector: str = Form(...),
        ciiu_code: str = Form(""),
        country: str = Form("Colombia"),
        department: str = Form(""),
        city: str = Form(...),
        employees: int = Form(0),
        contact_name: str = Form(""),
        contact_email: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_org")
        org = get_organization(session, int(user["organization_id"]))
        if not org:
            raise HTTPException(404, "Organización no encontrada")
        update_organization(
            session,
            org,
            actor_email=str(user["email"]),
            name=name,
            trade_name=trade_name,
            tax_id=tax_id,
            sector=sector,
            ciiu_code=ciiu_code,
            country=country,
            department=department,
            city=city,
            employees=employees,
            contact_name=contact_name,
            contact_email=contact_email,
        )
        session.commit()
        set_flash(request, "La información de la organización fue actualizada.")
        return RedirectResponse("/organizacion", status_code=303)
    @app.post("/sedes/nueva")
    def facility_create(
        request: Request,
        name: str = Form(...),
        facility_type: str = Form(...),
        city: str = Form(...),
        address: str = Form(""),
        employees: int = Form(0),
        ownership_percentage: float = Form(100),
        operational_control: str | None = Form(None),
        financial_control: str | None = Form(None),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_org")
        facility = create_facility(
            session,
            int(user["organization_id"]),
            actor_email=str(user["email"]),
            name=name,
            facility_type=facility_type,
            city=city,
            address=address,
            employees=employees,
            ownership_percentage=ownership_percentage,
            operational_control=operational_control == "on",
            financial_control=financial_control == "on",
        )
        session.commit()
        set_flash(request, "La nueva sede fue creada.")
        return RedirectResponse("/organizacion#sedes", status_code=303)
    @app.post("/sedes/{facility_id}/editar")
    def facility_edit(
        facility_id: int,
        request: Request,
        name: str = Form(...),
        facility_type: str = Form(...),
        city: str = Form(...),
        address: str = Form(""),
        employees: int = Form(0),
        ownership_percentage: float = Form(100),
        operational_control: str | None = Form(None),
        financial_control: str | None = Form(None),
        active: str | None = Form(None),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_org")
        facility = update_facility(
            session,
            int(user["organization_id"]),
            facility_id,
            actor_email=str(user["email"]),
            name=name,
            facility_type=facility_type,
            city=city,
            address=address,
            employees=employees,
            ownership_percentage=ownership_percentage,
            operational_control=operational_control == "on",
            financial_control=financial_control == "on",
            active=active == "on",
        )
        if not facility:
            raise HTTPException(404, "Sede no encontrada")
        session.commit()
        set_flash(request, f"La sede {facility.name} fue actualizada.")
        return RedirectResponse("/organizacion#sedes", status_code=303)
