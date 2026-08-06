from __future__ import annotations

from fastapi import Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .database import ActivityData, EmissionFactorVersion, EmissionSource, Inventory, get_db
from .factor_library import (
    build_factor_comparison_workbook,
    catalog_json,
    compare_factors,
    factor_catalog,
    factor_passport,
)


def _load_context(
    session: Session,
    organization_id: int,
    source_id: int | None,
    activity_data_id: int | None,
) -> tuple[EmissionSource | None, ActivityData | None]:
    source: EmissionSource | None = None
    record: ActivityData | None = None
    if source_id is not None:
        source = session.scalar(
            select(EmissionSource)
            .where(EmissionSource.id == source_id)
            .options(
                selectinload(EmissionSource.inventory).selectinload(Inventory.organization),
                selectinload(EmissionSource.activity_records),
            )
        )
        if not source or source.inventory.organization_id != organization_id:
            raise HTTPException(404, "Fuente no encontrada")
    if activity_data_id is not None:
        record = session.scalar(
            select(ActivityData)
            .where(ActivityData.id == activity_data_id)
            .options(selectinload(ActivityData.source).selectinload(EmissionSource.inventory).selectinload(Inventory.organization))
        )
        if not record or record.source.inventory.organization_id != organization_id:
            raise HTTPException(404, "Dato de actividad no encontrado")
        if source and record.source_id != source.id:
            raise HTTPException(400, "El dato no pertenece a la fuente seleccionada")
        source = source or record.source
    return source, record


def _context_query(source: EmissionSource | None, record: ActivityData | None) -> str:
    parts: list[str] = []
    if source:
        parts.append(f"source_id={source.id}")
    if record:
        parts.append(f"activity_data_id={record.id}")
    return "&".join(parts)


def register_factor_library_routes(app, templates, common_context, require_user, ensure_capability) -> None:
    @app.get("/metodologia/biblioteca-factores", response_class=HTMLResponse)
    def factor_library_page(
        request: Request,
        q: str = Query(""),
        sector: str = Query(""),
        country: str = Query(""),
        gas: str = Query(""),
        unit: str = Query(""),
        reporting_use: str = Query(""),
        quality: str = Query(""),
        readiness: str = Query(""),
        hierarchy: int | None = Query(None, ge=1, le=6),
        temporal_status: str = Query(""),
        data_year: int | None = Query(None, ge=1900, le=2100),
        source_id: int | None = Query(None),
        activity_data_id: int | None = Query(None),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "view_methodology")
        source, record = _load_context(session, int(user["organization_id"]), source_id, activity_data_id)
        summary = factor_catalog(
            session,
            query=q,
            sector=sector,
            country=country,
            gas=gas,
            unit=unit,
            reporting_use=reporting_use,
            quality=quality,
            readiness=readiness,
            hierarchy=hierarchy,
            temporal_status=temporal_status,
            data_year=data_year,
            source=source,
            record=record,
        )
        return templates.TemplateResponse(
            request=request,
            name="factor_library.html",
            context=common_context(
                request,
                session,
                user,
                "factor_library",
                summary=summary,
                source=source,
                record=record,
                context_query=_context_query(source, record),
            ),
        )

    @app.get("/metodologia/biblioteca-factores/{version_id}", response_class=HTMLResponse)
    def factor_passport_page(
        version_id: int,
        request: Request,
        source_id: int | None = Query(None),
        activity_data_id: int | None = Query(None),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "view_methodology")
        source, record = _load_context(session, int(user["organization_id"]), source_id, activity_data_id)
        version = session.scalar(
            select(EmissionFactorVersion)
            .where(EmissionFactorVersion.id == version_id)
            .options(selectinload(EmissionFactorVersion.factor), selectinload(EmissionFactorVersion.gas))
        )
        if not version:
            raise HTTPException(404, "Versión de factor no encontrada")
        passport = factor_passport(session, version, source=source, record=record)
        return templates.TemplateResponse(
            request=request,
            name="factor_passport.html",
            context=common_context(
                request,
                session,
                user,
                "factor_library",
                passport=passport,
                source=source,
                record=record,
                context_query=_context_query(source, record),
            ),
        )

    @app.get("/metodologia/biblioteca-factores/comparar/seleccion", response_class=HTMLResponse)
    def factor_compare_page(
        request: Request,
        ids: list[int] = Query(default=[]),
        source_id: int | None = Query(None),
        activity_data_id: int | None = Query(None),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "view_methodology")
        source, record = _load_context(session, int(user["organization_id"]), source_id, activity_data_id)
        comparison = compare_factors(session, ids, source=source, record=record)
        return templates.TemplateResponse(
            request=request,
            name="factor_compare.html",
            context=common_context(
                request,
                session,
                user,
                "factor_library",
                comparison=comparison,
                source=source,
                record=record,
                ids=ids,
                context_query=_context_query(source, record),
            ),
        )

    @app.get("/metodologia/biblioteca-factores/comparar/exportar.xlsx")
    def factor_compare_export(
        ids: list[int] = Query(default=[]),
        source_id: int | None = Query(None),
        activity_data_id: int | None = Query(None),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "view_methodology")
        source, record = _load_context(session, int(user["organization_id"]), source_id, activity_data_id)
        comparison = compare_factors(session, ids, source=source, record=record)
        content = build_factor_comparison_workbook(comparison)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="comparacion_factores_v0_54.xlsx"'},
        )

    @app.get("/api/metodologia/biblioteca-factores")
    def factor_library_api(
        q: str = Query(""),
        sector: str = Query(""),
        country: str = Query(""),
        gas: str = Query(""),
        unit: str = Query(""),
        reporting_use: str = Query(""),
        quality: str = Query(""),
        readiness: str = Query(""),
        hierarchy: int | None = Query(None, ge=1, le=6),
        temporal_status: str = Query(""),
        data_year: int | None = Query(None, ge=1900, le=2100),
        source_id: int | None = Query(None),
        activity_data_id: int | None = Query(None),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "view_methodology")
        source, record = _load_context(session, int(user["organization_id"]), source_id, activity_data_id)
        summary = factor_catalog(
            session,
            query=q,
            sector=sector,
            country=country,
            gas=gas,
            unit=unit,
            reporting_use=reporting_use,
            quality=quality,
            readiness=readiness,
            hierarchy=hierarchy,
            temporal_status=temporal_status,
            data_year=data_year,
            source=source,
            record=record,
        )
        return Response(content=catalog_json(summary), media_type="application/json")
