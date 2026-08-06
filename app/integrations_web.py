from __future__ import annotations

import json
import secrets
from datetime import UTC, date, datetime

from fastapi import Depends, Form, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .automations import hash_api_key
from .calculations import recalculate_source
from .database import (
    ActivityData,
    EmissionSource,
    IntegrationConnection,
    IntegrationEvent,
    Inventory,
    add_audit,
    get_db,
    refresh_progress,
)


class ActivityDataAPIInput(BaseModel):
    source_id: int
    period_start: date
    period_end: date
    value: float = Field(gt=0)
    unit: str
    data_origin: str = "Integración API"
    external_reference: str = ""
    notes: str = ""


def integration_from_key(session: Session, api_key: str) -> IntegrationConnection:
    digest = hash_api_key(api_key)
    integration = session.scalar(select(IntegrationConnection).where(
        IntegrationConnection.api_key_hash == digest,
        IntegrationConnection.active.is_(True),
    ))
    if not integration:
        raise HTTPException(401, "Clave API inválida o inactiva")
    return integration


def register_integration_routes(
    app,
    templates,
    common_context,
    require_user,
    ensure_capability,
    set_flash,
    ensure_inventory_editable,
    allowed_units: list[str],
) -> None:
    @app.get("/integraciones", response_class=HTMLResponse)
    def integrations_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_integrations")
        integrations = list(session.scalars(
            select(IntegrationConnection)
            .where(IntegrationConnection.organization_id == int(user["organization_id"]))
            .options(selectinload(IntegrationConnection.events))
            .order_by(IntegrationConnection.created_at.desc())
        ))
        recent_events = list(session.scalars(
            select(IntegrationEvent)
            .join(IntegrationConnection)
            .where(IntegrationConnection.organization_id == int(user["organization_id"]))
            .options(selectinload(IntegrationEvent.integration))
            .order_by(IntegrationEvent.created_at.desc()).limit(50)
        ))
        new_api_key = request.session.pop("new_api_key", None)
        sources = list(session.scalars(
            select(EmissionSource).join(Inventory)
            .where(Inventory.organization_id == int(user["organization_id"]))
            .order_by(EmissionSource.name)
        ))
        return templates.TemplateResponse(
            request=request,
            name="integrations.html",
            context=common_context(
                request, session, user, "integrations", integrations=integrations,
                recent_events=recent_events, new_api_key=new_api_key, sources=sources,
            ),
        )

    @app.post("/integraciones/nueva")
    def integration_create(
        request: Request,
        name: str = Form(...),
        provider: str = Form("API REST"),
        integration_type: str = Form("Entrada de datos"),
        endpoint_url: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_integrations")
        raw_key = "cth_" + secrets.token_urlsafe(28)
        is_api = provider == "API REST"
        integration = IntegrationConnection(
            organization_id=int(user["organization_id"]), name=name.strip(), provider=provider,
            integration_type=integration_type, endpoint_url=endpoint_url.strip(),
            status="Verificada" if is_api else "Configurada",
            api_key_hash=hash_api_key(raw_key) if is_api else "",
            api_key_prefix=raw_key[:12] if is_api else "",
            config_json=json.dumps({"scope": "activity_data"}) if is_api else "{}",
            last_test_at=datetime.now(UTC) if is_api else None,
            last_test_detail="Clave API generada y lista para recibir datos." if is_api else "Pendiente de credenciales y prueba externa.",
            active=True, created_by=str(user["email"]),
        )
        session.add(integration)
        session.flush()
        add_audit(session, int(user["organization_id"]), str(user["email"]), "CREAR", "Integración", integration.name, provider)
        session.commit()
        if is_api:
            request.session["new_api_key"] = raw_key
        set_flash(request, "Integración creada." + (" Copia la clave API: solo se mostrará una vez." if is_api else ""))
        return RedirectResponse("/integraciones", status_code=303)

    @app.post("/integraciones/{integration_id}/rotar-clave")
    def integration_rotate_key(integration_id: int, request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_integrations")
        integration = session.scalar(select(IntegrationConnection).where(
            IntegrationConnection.id == integration_id,
            IntegrationConnection.organization_id == int(user["organization_id"]),
        ))
        if not integration:
            raise HTTPException(404, "Integración no encontrada")
        raw_key = "cth_" + secrets.token_urlsafe(28)
        integration.api_key_hash = hash_api_key(raw_key)
        integration.api_key_prefix = raw_key[:12]
        integration.status = "Verificada"
        integration.last_test_at = datetime.now(UTC)
        integration.last_test_detail = "Clave API rotada correctamente."
        request.session["new_api_key"] = raw_key
        add_audit(session, int(user["organization_id"]), str(user["email"]), "ROTAR", "Clave API", integration.name)
        session.commit()
        set_flash(request, "Clave rotada. Copia la nueva clave: solo se mostrará una vez.")
        return RedirectResponse("/integraciones", status_code=303)

    @app.post("/integraciones/{integration_id}/estado")
    def integration_toggle(integration_id: int, request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_integrations")
        integration = session.scalar(select(IntegrationConnection).where(
            IntegrationConnection.id == integration_id,
            IntegrationConnection.organization_id == int(user["organization_id"]),
        ))
        if not integration:
            raise HTTPException(404, "Integración no encontrada")
        integration.active = not integration.active
        integration.status = "Verificada" if integration.active and integration.api_key_hash else ("Configurada" if integration.active else "Inactiva")
        session.commit()
        set_flash(request, f"Integración {'activada' if integration.active else 'desactivada'}.")
        return RedirectResponse("/integraciones", status_code=303)

    @app.post("/api/v1/activity-data")
    def api_activity_data_create(
        payload: ActivityDataAPIInput,
        x_api_key: str = Header(..., alias="X-API-Key"),
        session: Session = Depends(get_db),
    ):
        integration = integration_from_key(session, x_api_key)
        if payload.external_reference:
            previous_event = session.scalar(select(IntegrationEvent).where(
                IntegrationEvent.integration_id == integration.id,
                IntegrationEvent.external_reference == payload.external_reference,
                IntegrationEvent.status == "Recibido",
            ).order_by(IntegrationEvent.id.desc()))
            if previous_event:
                return {
                    "ok": True,
                    "duplicate": True,
                    "activity_data_id": previous_event.activity_data_id,
                    "external_reference": payload.external_reference,
                }
        source = session.scalar(
            select(EmissionSource).join(Inventory).where(
                EmissionSource.id == payload.source_id,
                Inventory.organization_id == integration.organization_id,
            ).options(selectinload(EmissionSource.inventory))
        )
        if not source:
            session.add(IntegrationEvent(
                integration_id=integration.id, status="Rechazado", event_type="Dato de actividad",
                detail=f"Fuente {payload.source_id} no pertenece a la organización.", external_reference=payload.external_reference,
            ))
            session.commit()
            raise HTTPException(404, "Fuente no encontrada para esta organización")
        ensure_inventory_editable(source.inventory)
        if payload.period_end < payload.period_start:
            raise HTTPException(400, "El periodo final no puede ser anterior al inicial")
        if payload.unit not in allowed_units:
            raise HTTPException(400, "Unidad no autorizada")
        record = ActivityData(
            source_id=source.id, period_start=payload.period_start, period_end=payload.period_end,
            value=payload.value, unit=payload.unit, data_origin=payload.data_origin,
            quality_level="B", is_estimated=False, notes=payload.notes,
            status="Cargado", created_by=f"integracion:{integration.name}",
        )
        session.add(record)
        session.flush()
        recalculate_source(session, source)
        refresh_progress(session, source.inventory)
        event = IntegrationEvent(
            integration_id=integration.id, activity_data_id=record.id, direction="Entrada", event_type="Dato de actividad", status="Recibido",
            detail=f"Registro {record.id} creado para {source.name}: {payload.value} {payload.unit}.",
            external_reference=payload.external_reference,
        )
        session.add(event)
        integration.last_test_at = datetime.now(UTC)
        integration.last_test_detail = "Última recepción API completada correctamente."
        add_audit(session, integration.organization_id, f"api:{integration.api_key_prefix}", "CREAR", "Dato de actividad", source.name, event.detail)
        session.commit()
        return {
            "ok": True,
            "activity_data_id": record.id,
            "source_id": source.id,
            "source": source.name,
            "inventory_id": source.inventory_id,
            "progress": source.progress,
        }

    @app.get("/api/v1/sources")
    def api_sources_list(x_api_key: str = Header(..., alias="X-API-Key"), session: Session = Depends(get_db)):
        integration = integration_from_key(session, x_api_key)
        sources = list(session.scalars(
            select(EmissionSource).join(Inventory)
            .where(Inventory.organization_id == integration.organization_id)
            .order_by(EmissionSource.name)
        ))
        return {"organization_id": integration.organization_id, "sources": [
            {"id": item.id, "name": item.name, "scope": item.scope, "category": item.category, "preferred_unit": item.preferred_unit}
            for item in sources
        ]}
