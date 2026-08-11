from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .calculations import recalculate_source
from .capture_guidance import capture_summary, is_activity_capture_source
from .config import settings
from .database import ActivityData, EmissionSource, EvidenceDocument, Inventory, add_audit, get_db, refresh_progress
from .period_close import assert_periods_editable
from .security import validate_upload_bytes
from .storage import StorageError, storage


def register_capture_routes(
    app,
    templates,
    common_context,
    require_user,
    set_flash,
    parse_date,
    get_inventory,
    ensure_inventory_editable,
    quality_from,
    safe_filename,
    allowed_upload_extensions,
    max_upload_size,
    allowed_units,
    data_origins,
) -> None:
    @app.get("/captura-guiada", response_class=HTMLResponse)
    def guided_capture_page(
        request: Request,
        source_id: int | None = None,
        copy_record_id: int | None = None,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        inventory = session.scalar(
            select(Inventory)
            .where(Inventory.id == get_inventory(session, user).id)
            .options(
                selectinload(Inventory.sources).selectinload(EmissionSource.facility),
                selectinload(Inventory.sources).selectinload(EmissionSource.activity_records).selectinload(ActivityData.evidence),
                selectinload(Inventory.documents),
            )
        )
        if not inventory:
            raise HTTPException(404, "Inventario no encontrado")
        summary = capture_summary(inventory)
        selected = next((item for item in summary["cards"] if item["source"].id == source_id), None)
        if not selected:
            selected = summary["next_action"]
        copy_record = None
        if copy_record_id:
            copy_record = session.scalar(
                select(ActivityData)
                .join(EmissionSource)
                .where(
                    ActivityData.id == copy_record_id,
                    EmissionSource.inventory_id == inventory.id,
                )
                .options(selectinload(ActivityData.source))
            )
            if copy_record:
                selected = next((item for item in summary["cards"] if item["source"].id == copy_record.source_id), selected)
        prefill = {
            "value": copy_record.value if copy_record else "",
            "unit": copy_record.unit if copy_record else (selected["profile"]["unit"] if selected else ""),
            "origin": copy_record.data_origin if copy_record else (selected["profile"]["origin"] if selected else "Registro operativo"),
            "uncertainty": copy_record.uncertainty_percentage if copy_record else 0,
            "uncertainty_basis": (
                f"Referencia del periodo {copy_record.period_start:%m/%Y}; requiere validación y soporte del nuevo periodo."
                if copy_record else ""
            ),
            "notes": (
                f"Valor prellenado desde {copy_record.period_start:%d/%m/%Y}–{copy_record.period_end:%d/%m/%Y}. Confirma antes de guardar."
                if copy_record else ""
            ),
            "is_estimated": bool(copy_record),
        }
        return templates.TemplateResponse(
            request=request,
            name="guided_capture.html",
            context=common_context(
                request,
                session,
                user,
                "guided_capture",
                inventory=inventory,
                summary=summary,
                selected=selected,
                copy_record=copy_record,
                prefill=prefill,
                documents=inventory.documents,
                allowed_units=allowed_units,
                data_origins=data_origins,
            ),
        )

    @app.get("/api/captura-guiada")
    def guided_capture_api(session: Session = Depends(get_db), user: dict = Depends(require_user)):
        inventory = session.scalar(
            select(Inventory)
            .where(Inventory.id == get_inventory(session, user).id)
            .options(selectinload(Inventory.sources).selectinload(EmissionSource.activity_records))
        )
        if not inventory:
            raise HTTPException(404, "Inventario no encontrado")
        summary = capture_summary(inventory)
        return JSONResponse({
            "inventory_id": inventory.id,
            "coverage": summary["coverage"],
            "support_coverage": summary["support_coverage"],
            "pending_sources": summary["pending_sources"],
            "sources": [
                {
                    "id": item["source"].id,
                    "name": item["source"].name,
                    "status": item["status"],
                    "coverage": item["coverage"],
                    "support_coverage": item["support_coverage"],
                    "next_start": item["next_start"].isoformat() if item["next_start"] else None,
                    "next_end": item["next_end"].isoformat() if item["next_end"] else None,
                    "expected_unit": item["profile"]["unit"],
                    "expected_evidence": item["profile"]["evidence"],
                }
                for item in summary["cards"]
            ],
        })

    @app.post("/captura-guiada/registrar")
    async def guided_capture_create(
        request: Request,
        source_id: int = Form(...),
        period_start: str = Form(...),
        period_end: str = Form(...),
        value: float = Form(...),
        unit: str = Form(...),
        data_origin: str = Form(...),
        evidence_id: int | None = Form(None),
        evidence_file: UploadFile | None = File(None),
        document_type: str = Form("Registro operativo"),
        is_estimated: str | None = Form(None),
        uncertainty_percentage: float = Form(0),
        uncertainty_basis: str = Form(""),
        notes: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        if not user["can_provide_data"]:
            raise HTTPException(403, "Tu rol no puede cargar datos")
        inventory = get_inventory(session, user)
        ensure_inventory_editable(inventory)
        source = session.scalar(select(EmissionSource).where(EmissionSource.id == source_id, EmissionSource.inventory_id == inventory.id))
        if not source:
            raise HTTPException(400, "Fuente inválida")
        if not is_activity_capture_source(source):
            raise HTTPException(409, "Esta fuente se gestiona desde Cadena de valor y no admite captura operativa directa")
        if unit not in allowed_units or data_origin not in data_origins:
            raise HTTPException(400, "Unidad u origen inválidos")
        start_date = parse_date(period_start)
        end_date = parse_date(period_end)
        if start_date > end_date or start_date < inventory.start_date or end_date > inventory.end_date:
            raise HTTPException(400, "El periodo no corresponde al inventario")
        try:
            assert_periods_editable(session, inventory.id, [(start_date, end_date)])
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        duplicate = session.scalar(select(ActivityData.id).where(ActivityData.source_id == source.id, ActivityData.period_start == start_date, ActivityData.period_end == end_date))
        if duplicate:
            set_flash(request, "Ya existe un registro para esa fuente y periodo.", "error")
            return RedirectResponse(f"/captura-guiada?source_id={source.id}", status_code=303)

        evidence = session.get(EvidenceDocument, evidence_id) if evidence_id else None
        if evidence and evidence.inventory_id != inventory.id:
            raise HTTPException(400, "Evidencia inválida")
        storage_key = ""
        if evidence_file and evidence_file.filename:
            original_name = safe_filename(evidence_file.filename)
            extension = Path(original_name).suffix.lower()
            if extension not in allowed_upload_extensions:
                set_flash(request, "Formato no permitido. Usa PDF, Excel, CSV, JPG o PNG.", "error")
                return RedirectResponse(f"/captura-guiada?source_id={source.id}", status_code=303)
            content = await evidence_file.read(max_upload_size + 1)
            if len(content) > max_upload_size:
                set_flash(request, f"El archivo supera el límite de {settings.max_upload_mb} MB.", "error")
                return RedirectResponse(f"/captura-guiada?source_id={source.id}", status_code=303)
            valid, message, detected_mime = validate_upload_bytes(original_name, content, evidence_file.content_type, allowed_upload_extensions)
            if not valid:
                set_flash(request, message, "error")
                return RedirectResponse(f"/captura-guiada?source_id={source.id}", status_code=303)
            storage_key = f"uploads/org_{user['organization_id']}/inventory_{inventory.id}/{datetime.now():%Y%m%d_%H%M%S}_{secrets.token_hex(4)}_{original_name}"
            try:
                storage.put_bytes(storage_key, content, detected_mime)
            except StorageError as exc:
                raise HTTPException(500, f"No fue posible almacenar la evidencia: {exc}") from exc
            evidence = EvidenceDocument(
                inventory_id=inventory.id,
                source_id=source.id,
                name=original_name,
                stored_name=storage_key,
                document_type=document_type.strip() or "Registro operativo",
                source_name=source.name,
                period_label=f"{start_date:%d/%m/%Y}–{end_date:%d/%m/%Y}",
                status="Cargado",
                uploaded_by=str(user["name"]),
                file_size=len(content),
                sha256=hashlib.sha256(content).hexdigest(),
                notes="Soporte cargado junto con el dato en captura guiada.",
            )
            session.add(evidence)
            session.flush()

        estimated = is_estimated == "on"
        record = ActivityData(
            source_id=source.id,
            evidence_id=evidence.id if evidence else None,
            period_start=start_date,
            period_end=end_date,
            value=max(value, 0),
            unit=unit,
            data_origin=data_origin,
            quality_level=quality_from(data_origin, estimated, evidence is not None),
            is_estimated=estimated,
            uncertainty_percentage=max(0, uncertainty_percentage),
            uncertainty_basis=uncertainty_basis.strip(),
            notes=notes.strip(),
            status="Provisional" if estimated else "Cargado",
            created_by=str(user["email"]),
        )
        session.add(record)
        try:
            session.flush()
            refresh_progress(session, inventory)
            result = recalculate_source(session, source)
            add_audit(
                session,
                int(user["organization_id"]),
                str(user["email"]),
                "CAPTURAR",
                "Dato y evidencia",
                f"{source.name} · {start_date:%Y-%m}",
                f"{record.value} {record.unit} · soporte {'sí' if evidence else 'no'} · {result['calculations']} cálculos",
            )
            session.commit()
        except Exception:
            session.rollback()
            if storage_key:
                storage.delete(storage_key)
            raise
        set_flash(request, "El dato y su soporte fueron registrados en una sola operación.")
        return RedirectResponse(f"/captura-guiada?source_id={source.id}", status_code=303)
