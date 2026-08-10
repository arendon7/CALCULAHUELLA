from __future__ import annotations

import math
from datetime import UTC, datetime

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .calculations import normalize_factor_output
from .database import add_audit, get_db
from .db.models import (
    EmissionFactor,
    EmissionFactorVersion,
    Gas,
    UnitConversion,
    UnitDefinition,
)


def register_methodology_admin_routes(
    app,
    templates,
    common_context,
    require_user,
    ensure_capability,
    set_flash,
    allowed_units,
) -> None:
    ALLOWED_UNITS = allowed_units
    @app.get("/metodologia", response_class=HTMLResponse)
    def methodology_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "view_methodology")
        factors = list(
            session.scalars(
                select(EmissionFactor)
                .options(selectinload(EmissionFactor.versions).selectinload(EmissionFactorVersion.gas))
                .order_by(EmissionFactor.activity_type, EmissionFactor.name)
            )
        )
        units = list(session.scalars(select(UnitDefinition).order_by(UnitDefinition.dimension, UnitDefinition.code)))
        conversions = list(session.scalars(select(UnitConversion).where(UnitConversion.active.is_(True)).order_by(UnitConversion.from_unit, UnitConversion.to_unit)))
        gases = list(session.scalars(select(Gas).options(selectinload(Gas.gwp_values)).order_by(Gas.code)))
        return templates.TemplateResponse(
            request=request,
            name="methodology.html",
            context=common_context(
                request,
                session,
                user,
                "methodology",
                factors=factors,
                units=units,
                conversions=conversions,
                gases=gases,
                allowed_units=ALLOWED_UNITS,
            ),
        )

    @app.post("/metodologia/factores/nuevo")
    def factor_create(
        request: Request,
        name: str = Form(...),
        activity_type: str = Form(...),
        gas_id: int = Form(...),
        value: float = Form(...),
        input_unit: str = Form(...),
        output_unit: str = Form("kg gas"),
        version: str = Form("1.0"),
        source_organization: str = Form(...),
        source_document: str = Form(""),
        publication_year: int = Form(...),
        geographic_scope: str = Form("Colombia"),
        technology_scope: str = Form("Genérico"),
        uncertainty_percentage: float = Form(0),
        notes: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "view_methodology")
        if input_unit not in ALLOWED_UNITS:
            raise HTTPException(400, "Unidad no autorizada")
        gas = session.get(Gas, gas_id)
        if not gas or not math.isfinite(value) or value < 0:
            raise HTTPException(400, "Gas o valor inválido")
        if not math.isfinite(uncertainty_percentage) or uncertainty_percentage < 0:
            raise HTTPException(400, "La incertidumbre debe ser un número finito mayor o igual a cero")
        normalized_output, output_error = normalize_factor_output(1.0, output_unit, gas.code)
        if normalized_output is None:
            raise HTTPException(400, output_error)
        factor = session.scalar(select(EmissionFactor).where(EmissionFactor.name == name.strip()))
        if not factor:
            factor = EmissionFactor(name=name.strip(), activity_type=activity_type.strip(), country="Colombia", sector="Multisectorial", status="Activo", is_demo=False)
            session.add(factor)
            session.flush()
        duplicate = session.scalar(select(EmissionFactorVersion).where(EmissionFactorVersion.factor_id == factor.id, EmissionFactorVersion.version == version.strip(), EmissionFactorVersion.gas_id == gas.id))
        if duplicate:
            set_flash(request, "Ya existe esa versión para el gas seleccionado.", "error")
            return RedirectResponse("/metodologia", status_code=303)
        factor_version = EmissionFactorVersion(
            factor_id=factor.id,
            gas_id=gas.id,
            version=version.strip(),
            value=value,
            input_unit=input_unit,
            output_unit=output_unit.strip(),
            source_organization=source_organization.strip(),
            source_document=source_document.strip(),
            publication_year=publication_year,
            geographic_scope=geographic_scope.strip(),
            technology_scope=technology_scope.strip(),
            uncertainty_percentage=max(0, uncertainty_percentage),
            status="Pendiente de revisión",
            notes=notes.strip(),
        )
        session.add(factor_version)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "CREAR", "Factor", factor.name, f"Versión {factor_version.version} · {gas.code} · pendiente")
        session.commit()
        set_flash(request, "El factor fue creado como pendiente de revisión.")
        return RedirectResponse("/metodologia", status_code=303)

    @app.post("/metodologia/factores/{version_id}/estado")
    def factor_status_update(
        version_id: int,
        request: Request,
        status: str = Form(...),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        if not user["can_review"]:
            raise HTTPException(403, "Solo un revisor puede aprobar factores")
        factor_version = session.scalar(select(EmissionFactorVersion).where(EmissionFactorVersion.id == version_id).options(selectinload(EmissionFactorVersion.factor)))
        if not factor_version:
            raise HTTPException(404, "Factor no encontrado")
        if status not in {"Pendiente de revisión", "Aprobado", "Retirado"}:
            raise HTTPException(400, "Estado inválido")
        if status == "Aprobado":
            normalized_output, output_error = normalize_factor_output(
                1.0,
                factor_version.output_unit,
                factor_version.gas.code,
            )
            if normalized_output is None:
                raise HTTPException(409, f"El factor no puede aprobarse: {output_error}")
            if not math.isfinite(factor_version.value) or factor_version.value < 0:
                raise HTTPException(409, "El factor no puede aprobarse porque su valor no es válido")
        factor_version.status = status
        factor_version.approved_by = str(user["name"]) if status == "Aprobado" else factor_version.approved_by
        factor_version.approved_at = datetime.now(UTC) if status == "Aprobado" else factor_version.approved_at
        add_audit(session, int(user["organization_id"]), str(user["email"]), "REVISAR", "Factor", factor_version.factor.name, f"Estado {status}")
        session.commit()
        set_flash(request, "El estado del factor fue actualizado.")
        return RedirectResponse("/metodologia", status_code=303)

    @app.post("/metodologia/conversiones/nueva")
    def conversion_create(
        request: Request,
        from_unit: str = Form(...),
        to_unit: str = Form(...),
        multiplier: float = Form(...),
        source: str = Form("Conversión interna aprobada"),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "view_methodology")
        if from_unit == to_unit or not math.isfinite(multiplier) or multiplier <= 0:
            raise HTTPException(400, "Conversión inválida")
        source_definition = session.scalar(select(UnitDefinition).where(UnitDefinition.code == from_unit))
        target_definition = session.scalar(select(UnitDefinition).where(UnitDefinition.code == to_unit))
        if not source_definition or not target_definition or source_definition.dimension != target_definition.dimension:
            raise HTTPException(400, "Las unidades no existen o tienen dimensiones incompatibles")
        conversion = session.scalar(select(UnitConversion).where(UnitConversion.from_unit == from_unit, UnitConversion.to_unit == to_unit))
        if conversion:
            conversion.multiplier = multiplier
            conversion.source = source.strip()
            conversion.active = True
        else:
            session.add(UnitConversion(from_unit=from_unit, to_unit=to_unit, multiplier=multiplier, source=source.strip(), active=True))
        add_audit(session, int(user["organization_id"]), str(user["email"]), "CONFIGURAR", "Conversión", f"{from_unit} → {to_unit}", f"Multiplicador {multiplier:g}")
        session.commit()
        set_flash(request, "La conversión fue guardada.")
        return RedirectResponse("/metodologia", status_code=303)
