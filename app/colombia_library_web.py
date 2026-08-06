from __future__ import annotations

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from .colombia_library import (
    build_colombia_workbook,
    calculate_biogas_balance,
    calculate_combustion,
    calculate_fertilizer,
    calculate_wastewater,
    colombia_library_summary,
    summary_json,
)
from .database import get_db


def register_colombia_library_routes(app, templates, common_context, require_user, ensure_capability) -> None:
    @app.get("/metodologia/colombia", response_class=HTMLResponse)
    def colombia_library_page(
        request: Request,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "view_methodology")
        return templates.TemplateResponse(
            request=request,
            name="colombia_library.html",
            context=common_context(request, session, user, "colombia_library", summary=colombia_library_summary(session), result=None, calculator=None, error=None),
        )

    def _render(request: Request, session: Session, user: dict, calculator: str, result=None, error=None):
        return templates.TemplateResponse(
            request=request,
            name="colombia_library.html",
            context=common_context(request, session, user, "colombia_library", summary=colombia_library_summary(session), result=result, calculator=calculator, error=error),
        )

    @app.post("/metodologia/colombia/calcular-combustion", response_class=HTMLResponse)
    def colombia_combustion(
        request: Request,
        factor_code: str = Form(...),
        amount: float = Form(...),
        amount_unit: str = Form(...),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "view_methodology")
        try:
            return _render(request, session, user, "combustion", calculate_combustion(factor_code, amount, amount_unit))
        except ValueError as exc:
            return _render(request, session, user, "combustion", error=str(exc))

    @app.post("/metodologia/colombia/calcular-aguas", response_class=HTMLResponse)
    def colombia_wastewater(
        request: Request,
        organic_load_kg: float = Form(...),
        basis: str = Form(...),
        mcf: float = Form(...),
        recovered_ch4_kg: float = Form(0),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "view_methodology")
        try:
            return _render(request, session, user, "wastewater", calculate_wastewater(organic_load_kg, basis, mcf, recovered_ch4_kg))
        except ValueError as exc:
            return _render(request, session, user, "wastewater", error=str(exc))

    @app.post("/metodologia/colombia/calcular-fertilizante", response_class=HTMLResponse)
    def colombia_fertilizer(
        request: Request,
        nitrogen_kg: float = Form(...),
        climate: str = Form(...),
        input_type: str = Form(...),
        include_volatilization: bool = Form(False),
        include_leaching: bool = Form(False),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "view_methodology")
        try:
            return _render(request, session, user, "fertilizer", calculate_fertilizer(nitrogen_kg, climate, input_type, include_volatilization, include_leaching))
        except ValueError as exc:
            return _render(request, session, user, "fertilizer", error=str(exc))

    @app.post("/metodologia/colombia/calcular-biogas", response_class=HTMLResponse)
    def colombia_biogas(
        request: Request,
        produced_m3: float = Form(...),
        used_m3: float = Form(0),
        flared_m3: float = Form(0),
        vented_m3: float = Form(0),
        methane_fraction: float = Form(0.6),
        leakage_percent: float = Form(0),
        methane_density_kg_m3: float = Form(0.7168),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "view_methodology")
        try:
            return _render(request, session, user, "biogas", calculate_biogas_balance(produced_m3, used_m3, flared_m3, vented_m3, methane_fraction, leakage_percent, methane_density_kg_m3))
        except ValueError as exc:
            return _render(request, session, user, "biogas", error=str(exc))

    @app.get("/metodologia/colombia/exportar.xlsx")
    def colombia_export(session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "view_methodology")
        return Response(
            content=build_colombia_workbook(colombia_library_summary(session)),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="biblioteca_colombia_v0_28.xlsx"'},
        )

    @app.get("/api/metodologia/colombia")
    def colombia_api(session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "view_methodology")
        return Response(content=summary_json(colombia_library_summary(session)), media_type="application/json")
