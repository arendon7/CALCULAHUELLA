from __future__ import annotations

import json
import re
import secrets
import time
from pathlib import Path

from fastapi import Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .database import DataImportBatch, DataQualityFinding, Inventory, OperationalImportProfile, get_db
from .operational_imports import (
    ALLOWED_ORIGINS,
    MAPPING_FIELDS,
    apply_operational_batch,
    batch_errors_csv,
    build_operational_template,
    create_operational_batch,
    inspect_import_file,
    operational_import_summary,
    profile_payload,
    suggest_mapping,
    update_operational_row,
)
from .security import validate_upload_bytes

STAGE_TOKEN = re.compile(r"^[A-Za-z0-9_-]{20,80}$")
STAGE_TTL_SECONDS = 24 * 60 * 60


def _normalized_delimiter(value: str) -> str:
    if value in {"tab", "\\t"}:
        return "\t"
    return value


def register_operational_import_routes(
    app,
    templates,
    common_context,
    require_user,
    set_flash,
    instance_dir: Path,
    max_upload_size: int,
) -> None:
    staging_dir = instance_dir / "import_staging"
    staging_dir.mkdir(parents=True, exist_ok=True)

    def _can_manage(user: dict) -> bool:
        return bool(user.get("can_provide_data") or user.get("can_manage_sources") or user.get("can_manage_inventory"))

    def _require_manage(user: dict) -> None:
        if not _can_manage(user):
            raise HTTPException(403, "Tu rol no puede cargar ni aplicar datos operativos.")

    def _clean_staging() -> None:
        threshold = time.time() - STAGE_TTL_SECONDS
        for path in staging_dir.glob("stage_*"):
            try:
                if path.stat().st_mtime < threshold:
                    path.unlink(missing_ok=True)
            except OSError:
                continue

    def _stage_paths(token: str) -> tuple[Path, Path]:
        if not STAGE_TOKEN.fullmatch(token):
            raise ValueError("Token de carga inválido.")
        return staging_dir / f"stage_{token}.bin", staging_dir / f"stage_{token}.json"

    def _save_stage(organization_id: int, filename: str, content_type: str, content: bytes) -> str:
        _clean_staging()
        token = secrets.token_urlsafe(24)
        data_path, meta_path = _stage_paths(token)
        data_path.write_bytes(content)
        meta_path.write_text(json.dumps({
            "organization_id": organization_id,
            "filename": filename,
            "content_type": content_type,
            "created_at": time.time(),
        }, ensure_ascii=False))
        return token

    def _load_stage(token: str, organization_id: int) -> tuple[dict, bytes]:
        data_path, meta_path = _stage_paths(token)
        if not data_path.exists() or not meta_path.exists():
            raise ValueError("La previsualización venció o ya no existe. Carga nuevamente el archivo.")
        meta = json.loads(meta_path.read_text())
        if int(meta.get("organization_id", -1)) != organization_id:
            raise ValueError("La previsualización no pertenece a la organización activa.")
        if float(meta.get("created_at", 0)) < time.time() - STAGE_TTL_SECONDS:
            data_path.unlink(missing_ok=True)
            meta_path.unlink(missing_ok=True)
            raise ValueError("La previsualización venció. Carga nuevamente el archivo.")
        return meta, data_path.read_bytes()

    def _delete_stage(token: str) -> None:
        try:
            data_path, meta_path = _stage_paths(token)
            data_path.unlink(missing_ok=True)
            meta_path.unlink(missing_ok=True)
        except ValueError:
            pass

    def _staging_context(
        session: Session,
        organization_id: int,
        token: str,
        profile_id: int | None = None,
        sheet_name: str = "",
        delimiter: str = "",
        header_row: int = 0,
    ) -> dict:
        meta, content = _load_stage(token, organization_id)
        profile = None
        if profile_id:
            profile = session.scalar(select(OperationalImportProfile).where(
                OperationalImportProfile.id == profile_id,
                OperationalImportProfile.organization_id == organization_id,
                OperationalImportProfile.active.is_(True),
            ))
        profile_data = profile_payload(profile) if profile else None
        selected_sheet = sheet_name or (profile_data["sheet_name"] if profile_data else "")
        selected_delimiter = _normalized_delimiter(delimiter or (profile_data["delimiter"] if profile_data else "auto"))
        selected_header_row = header_row if header_row > 0 else int(profile_data["header_row"] if profile_data else 1)
        inspection = inspect_import_file(
            content,
            meta["filename"],
            sheet_name=selected_sheet,
            delimiter=selected_delimiter,
            header_row=selected_header_row,
            preview_rows=8,
        )
        mapping = suggest_mapping(inspection["headers"])
        defaults = {"origin": "Registro operativo", "duplicate_policy": "reject", "estimated": False}
        if profile_data:
            mapping.update({key: value for key, value in profile_data["mapping"].items() if value in inspection["headers"]})
            defaults.update(profile_data["defaults"])
        return {
            "token": token,
            "filename": meta["filename"],
            "content_type": meta.get("content_type", ""),
            "inspection": inspection,
            "mapping": mapping,
            "defaults": defaults,
            "profile": profile,
        }

    @app.get("/cargas-operativas", response_class=HTMLResponse)
    def operational_import_page(
        request: Request,
        batch_id: int | None = None,
        inventory_id: int | None = None,
        stage: str = "",
        profile_id: int | None = None,
        sheet_name: str = "",
        delimiter: str = "",
        header_row: int = 0,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        try:
            summary = operational_import_summary(session, int(user["organization_id"]), inventory_id, batch_id)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        staging = None
        if stage:
            try:
                staging = _staging_context(
                    session,
                    int(user["organization_id"]),
                    stage,
                    profile_id,
                    sheet_name,
                    delimiter,
                    header_row,
                )
            except ValueError as exc:
                set_flash(request, str(exc), "error")
        return templates.TemplateResponse(
            request=request,
            name="operational_imports.html",
            context=common_context(
                request,
                session,
                user,
                "operational_imports",
                summary=summary,
                staging=staging,
                can_manage=_can_manage(user),
                mapping_fields=MAPPING_FIELDS,
                origins=sorted(ALLOWED_ORIGINS),
            ),
        )

    @app.get("/cargas-operativas/plantilla.xlsx")
    def operational_template(
        inventory_id: int | None = None,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        summary = operational_import_summary(session, int(user["organization_id"]), inventory_id)
        content = build_operational_template(summary["inventory"])
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="plantilla_carga_operativa_{summary["inventory"].id}.xlsx"'},
        )

    @app.post("/cargas-operativas/previsualizar")
    async def operational_preview(
        request: Request,
        file: UploadFile = File(...),
        profile_id: str = Form(""),
        inventory_id: int = Form(...),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        _require_manage(user)
        inventory = session.scalar(select(Inventory).where(
            Inventory.id == inventory_id,
            Inventory.organization_id == int(user["organization_id"]),
        ))
        if not inventory:
            raise HTTPException(404, "Inventario no encontrado.")
        content = await file.read(max_upload_size + 1)
        if len(content) > max_upload_size:
            set_flash(request, "El archivo supera el tamaño máximo permitido.", "error")
            return RedirectResponse(f"/cargas-operativas?inventory_id={inventory_id}", status_code=303)
        filename = file.filename or "carga"
        valid, message, detected = validate_upload_bytes(filename, content, file.content_type, {".csv", ".xlsx"})
        if not valid:
            set_flash(request, message, "error")
            return RedirectResponse(f"/cargas-operativas?inventory_id={inventory_id}", status_code=303)
        try:
            # Fail early before persisting temporary content.
            inspect_import_file(content, filename)
            token = _save_stage(int(user["organization_id"]), filename, detected, content)
        except ValueError as exc:
            set_flash(request, str(exc), "error")
            return RedirectResponse(f"/cargas-operativas?inventory_id={inventory_id}", status_code=303)
        query = f"stage={token}&inventory_id={inventory_id}"
        if profile_id.isdigit():
            query += f"&profile_id={int(profile_id)}"
        return RedirectResponse(f"/cargas-operativas?{query}", status_code=303)

    @app.post("/cargas-operativas/validar")
    def operational_validate(
        request: Request,
        stage_token: str = Form(...),
        inventory_id: int = Form(...),
        source_sheet: str = Form(""),
        delimiter: str = Form("auto"),
        header_row: int = Form(1),
        map_source: str = Form(""),
        map_facility: str = Form(""),
        map_period_start: str = Form(""),
        map_period_end: str = Form(""),
        map_value: str = Form(""),
        map_unit: str = Form(""),
        map_origin: str = Form(""),
        map_estimated: str = Form(""),
        map_evidence: str = Form(""),
        map_notes: str = Form(""),
        default_source_id: str = Form(""),
        default_unit: str = Form(""),
        default_origin: str = Form("Registro operativo"),
        default_estimated: bool = Form(False),
        duplicate_policy: str = Form("reject"),
        profile_id: str = Form(""),
        profile_name: str = Form(""),
        save_profile: bool = Form(False),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        _require_manage(user)
        inventory = session.scalar(
            select(Inventory)
            .where(Inventory.id == inventory_id, Inventory.organization_id == int(user["organization_id"]))
            .options(selectinload(Inventory.sources))
        )
        if not inventory:
            raise HTTPException(404, "Inventario no encontrado.")
        try:
            meta, content = _load_stage(stage_token, int(user["organization_id"]))
            mapping = {
                "source": map_source,
                "facility": map_facility,
                "period_start": map_period_start,
                "period_end": map_period_end,
                "value": map_value,
                "unit": map_unit,
                "origin": map_origin,
                "estimated": map_estimated,
                "evidence": map_evidence,
                "notes": map_notes,
            }
            defaults = {
                "source_id": default_source_id,
                "unit": default_unit,
                "origin": default_origin,
                "estimated": default_estimated,
                "duplicate_policy": duplicate_policy,
            }
            batch = create_operational_batch(
                session,
                organization_id=int(user["organization_id"]),
                inventory=inventory,
                filename=meta["filename"],
                content=content,
                user_email=str(user["email"]),
                mapping=mapping,
                defaults=defaults,
                sheet_name=source_sheet,
                delimiter=_normalized_delimiter(delimiter),
                header_row=header_row,
                profile_name=profile_name,
                profile_id=int(profile_id) if profile_id.isdigit() else None,
                save_profile=save_profile,
            )
            session.commit()
            _delete_stage(stage_token)
            level = "error" if batch.error_rows else "success"
            set_flash(request, f"Lote {batch.code}: {batch.total_rows} filas, {batch.error_rows} errores y {batch.warning_rows} advertencias.", level)
            return RedirectResponse(f"/cargas-operativas?batch_id={batch.id}&inventory_id={inventory_id}", status_code=303)
        except ValueError as exc:
            session.rollback()
            set_flash(request, str(exc), "error")
            return RedirectResponse(f"/cargas-operativas?stage={stage_token}&inventory_id={inventory_id}", status_code=303)

    @app.post("/cargas-operativas/lotes/{batch_id}/filas/{row_id}/corregir")
    def operational_correct_row(
        batch_id: int,
        row_id: int,
        request: Request,
        source_id: str = Form(""),
        period_start: str = Form(""),
        period_end: str = Form(""),
        value: str = Form(""),
        unit: str = Form(""),
        origin: str = Form("Registro operativo"),
        estimated: bool = Form(False),
        evidence: str = Form(""),
        notes: str = Form(""),
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        _require_manage(user)
        try:
            row = update_operational_row(
                session,
                organization_id=int(user["organization_id"]),
                batch_id=batch_id,
                row_id=row_id,
                user_email=str(user["email"]),
                source_id=source_id,
                period_start=period_start,
                period_end=period_end,
                value=value,
                unit=unit,
                origin=origin,
                estimated=estimated,
                evidence=evidence,
                notes=notes,
            )
            session.commit()
            level = "error" if row.status == "Error" else "success"
            set_flash(request, f"Fila {row.row_number} revalidada: {row.status}.", level)
            return RedirectResponse(
                f"/cargas-operativas?inventory_id={row.batch.inventory_id}&batch_id={batch_id}#fila-{row.id}",
                status_code=303,
            )
        except ValueError as exc:
            session.rollback()
            set_flash(request, str(exc), "error")
            return RedirectResponse(f"/cargas-operativas?batch_id={batch_id}#detalle-lote", status_code=303)

    @app.post("/cargas-operativas/lotes/{batch_id}/aplicar")
    def operational_apply(
        batch_id: int,
        request: Request,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        _require_manage(user)
        try:
            batch = apply_operational_batch(session, int(user["organization_id"]), batch_id, str(user["email"]))
            session.commit()
            set_flash(request, f"Lote {batch.code} aplicado: {batch.applied_rows} registros actualizados.")
            return RedirectResponse(f"/cargas-operativas?batch_id={batch.id}&inventory_id={batch.inventory_id}", status_code=303)
        except ValueError as exc:
            session.rollback()
            set_flash(request, str(exc), "error")
            return RedirectResponse(f"/cargas-operativas?batch_id={batch_id}", status_code=303)

    @app.post("/cargas-operativas/perfiles/{profile_id}/estado")
    def operational_profile_status(
        profile_id: int,
        request: Request,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        _require_manage(user)
        profile = session.scalar(select(OperationalImportProfile).where(
            OperationalImportProfile.id == profile_id,
            OperationalImportProfile.organization_id == int(user["organization_id"]),
        ))
        if not profile:
            raise HTTPException(404, "Perfil no encontrado.")
        profile.active = not profile.active
        session.commit()
        set_flash(request, f"Perfil '{profile.name}' {'activado' if profile.active else 'desactivado'}.")
        return RedirectResponse("/cargas-operativas", status_code=303)

    @app.get("/cargas-operativas/lotes/{batch_id}/errores.csv")
    def operational_errors(
        batch_id: int,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        batch = session.scalar(
            select(DataImportBatch)
            .where(
                DataImportBatch.id == batch_id,
                DataImportBatch.organization_id == int(user["organization_id"]),
                DataImportBatch.execution_id.is_(None),
            )
            .options(
                selectinload(DataImportBatch.findings).selectinload(DataQualityFinding.row),
            )
        )
        if not batch:
            raise HTTPException(404, "Lote no encontrado.")
        return Response(
            content=batch_errors_csv(batch),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="hallazgos_{batch.code}.csv"'},
        )
