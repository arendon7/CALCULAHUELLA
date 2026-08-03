from __future__ import annotations

import csv
import hashlib
import json
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .storage import storage
from .config import settings

from .database import (
    ActivityData,
    EmissionCalculation,
    EmissionFactorVersion,
    EmissionSource,
    EvidenceDocument,
    Inventory,
    InventoryDecision,
    ReportArtifact,
    ReviewObservation,
    VerificationFinding,
    SupplierCampaign,
    SupplierDataRequest,
    SupplierResponse,
    ComplianceAssessment,
    ComplianceRequirement,
    DocumentControlRecord,
    InventoryMethodologySnapshot,
    INSTANCE_DIR,
)


def _write_csv(path: Path, headers: list[str], rows: list[list[object]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def create_verification_package(session: Session, inventory: Inventory, generated_by: str) -> ReportArtifact:
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    work = INSTANCE_DIR / f"verification_{inventory.id}_{stamp}"
    work.mkdir(parents=True, exist_ok=True)
    evidence_dir = work / "evidencias"
    reports_dir = work / "informes"
    evidence_dir.mkdir(exist_ok=True)
    reports_dir.mkdir(exist_ok=True)

    sources = list(session.scalars(select(EmissionSource).where(EmissionSource.inventory_id == inventory.id)))
    records = list(session.scalars(
        select(ActivityData).join(EmissionSource).where(EmissionSource.inventory_id == inventory.id)
    ))
    calculations = list(session.scalars(
        select(EmissionCalculation).join(ActivityData).join(EmissionSource).where(EmissionSource.inventory_id == inventory.id)
    ))
    documents = list(session.scalars(select(EvidenceDocument).where(EvidenceDocument.inventory_id == inventory.id)))
    observations = list(session.scalars(select(ReviewObservation).where(ReviewObservation.inventory_id == inventory.id)))
    findings = list(session.scalars(select(VerificationFinding).where(VerificationFinding.inventory_id == inventory.id)))
    decisions = list(session.scalars(select(InventoryDecision).where(InventoryDecision.inventory_id == inventory.id)))
    reports = list(session.scalars(select(ReportArtifact).where(ReportArtifact.inventory_id == inventory.id)))
    supplier_requests = list(session.scalars(
        select(SupplierDataRequest).join(SupplierCampaign).where(SupplierCampaign.inventory_id == inventory.id)
    ))
    supplier_responses = list(session.scalars(
        select(SupplierResponse).join(SupplierDataRequest).join(SupplierCampaign).where(SupplierCampaign.inventory_id == inventory.id)
    ))
    compliance = list(session.scalars(
        select(ComplianceAssessment).where(ComplianceAssessment.inventory_id == inventory.id).join(ComplianceRequirement)
    ))
    controlled_documents = list(session.scalars(
        select(DocumentControlRecord).where(DocumentControlRecord.organization_id == inventory.organization_id,
                                             (DocumentControlRecord.inventory_id == inventory.id) | (DocumentControlRecord.inventory_id.is_(None)))
    ))
    methodology_snapshots = list(session.scalars(
        select(InventoryMethodologySnapshot).where(InventoryMethodologySnapshot.inventory_id == inventory.id)
    ))

    _write_csv(work / "01_fuentes.csv", ["ID", "Fuente", "Alcance", "Categoría", "Sede", "Incluida", "Progreso", "Emisiones tCO2e"], [
        [item.id, item.name, item.scope, item.category, item.facility.name if item.facility else "Corporativo", item.included, item.progress, item.emissions]
        for item in sources
    ])
    _write_csv(work / "02_datos_actividad.csv", ["ID", "Fuente", "Inicio", "Fin", "Valor", "Unidad", "Origen", "Calidad", "Estimado", "Evidencia ID"], [
        [item.id, item.source.name, item.period_start, item.period_end, item.value, item.unit, item.data_origin, item.quality_level, item.is_estimated, item.evidence_id or ""]
        for item in records
    ])
    _write_csv(work / "03_calculos.csv", ["ID", "Dato ID", "Factor versión ID", "Valor original", "Unidad", "Valor normalizado", "Unidad normalizada", "Gas", "GWP", "kg CO2e", "Fórmula", "Estado", "Alerta"], [
        [item.id, item.activity_data_id, item.factor_version_id, item.original_value, item.original_unit, item.normalized_value, item.normalized_unit, item.gas_code, item.gwp_value, item.co2e_kg, item.formula_snapshot, item.status, item.warning]
        for item in calculations
    ])
    factor_ids = {item.factor_version_id for item in calculations}
    factors = list(session.scalars(select(EmissionFactorVersion).where(EmissionFactorVersion.id.in_(factor_ids)))) if factor_ids else []
    _write_csv(work / "04_factores.csv", ["ID", "Factor", "Versión", "Gas", "Valor", "Unidad entrada", "Unidad salida", "Fuente", "Año", "Estado"], [
        [item.id, item.factor.name, item.version, item.gas.code, item.value, item.input_unit, item.output_unit, item.source_organization, item.publication_year, item.status]
        for item in factors
    ])
    _write_csv(work / "05_evidencias.csv", ["ID", "Nombre", "Tipo", "Fuente", "Periodo", "Estado", "SHA256", "Tamaño", "Archivo incluido"], [
        [item.id, item.name, item.document_type, item.source.name if item.source else "Corporativo", item.period_label, item.status, item.sha256, item.file_size, bool(item.stored_name and storage.exists(item.stored_name))]
        for item in documents
    ])
    _write_csv(work / "06_observaciones_internas.csv", ["ID", "Título", "Entidad", "Severidad", "Estado", "Responsable", "Respuesta", "Resolución"], [
        [item.id, item.title, item.entity_label, item.severity, item.status, item.assigned_to, item.response, item.resolution]
        for item in observations
    ])
    _write_csv(work / "07_hallazgos_verificacion.csv", ["ID", "Título", "Tipo", "Severidad", "Estado", "Verificador", "Respuesta de gestión", "Conclusión"], [
        [item.id, item.title, item.finding_type, item.severity, item.status, item.verifier_email, item.management_response, item.conclusion]
        for item in findings
    ])
    _write_csv(work / "08_decisiones.csv", ["Tipo", "Decisión", "Comentarios", "Responsable", "Fecha", "Versión"], [
        [item.decision_type, item.decision, item.comments, item.decided_by, item.decided_at, item.inventory_version]
        for item in decisions
    ])
    _write_csv(work / "09_solicitudes_proveedores.csv", ["ID", "Campaña", "Proveedor", "Producto/servicio", "Cantidad", "Unidad", "Gasto COP", "Estado", "Fecha límite"], [
        [item.id, item.campaign.name, item.supplier.name, item.product_service, item.quantity, item.unit, item.spend_cop, item.status, item.due_date]
        for item in supplier_requests
    ])
    _write_csv(work / "10_respuestas_proveedores.csv", ["ID", "Proveedor", "Método", "Actividad", "Unidad", "Factor", "Unidad factor", "tCO2e", "Metodología", "Límite", "Verificada", "Calidad", "Revisión", "SHA256 evidencia"], [
        [item.id, item.request.supplier.name, item.method, item.activity_value, item.activity_unit, item.emission_factor, item.factor_unit, item.calculated_emissions_tco2e, item.methodology, item.boundary, item.verified, item.quality_level, item.review_status, item.evidence_sha256]
        for item in supplier_responses
    ])
    _write_csv(work / "11_matriz_cumplimiento.csv", ["Marco", "Código", "Requisito", "Estado", "Responsable", "Evidencia ID", "Notas", "Actualizado por"], [
        [item.requirement.framework, item.requirement.code, item.requirement.title, item.status, item.owner, item.evidence_id or "", item.notes, item.updated_by]
        for item in compliance
    ])
    _write_csv(work / "12_registro_documental.csv", ["Código", "Título", "Categoría", "Versión", "Propietario", "Confidencialidad", "Retención años", "Revisión", "Estado", "SHA256"], [
        [item.document_code, item.title, item.category, item.version, item.owner, item.confidentiality, item.retention_years, item.review_due or "", item.status, item.sha256]
        for item in controlled_documents
    ])
    _write_csv(work / "13_snapshots_metodologicos.csv", ["Nombre", "Estado", "Metodología", "Versión", "GWP", "Consolidación", "Materialidad", "Aprobado por", "Fecha"], [
        [item.snapshot_name, item.status, item.methodology_name, item.methodology_version, item.gwp_version, item.consolidation_approach, item.materiality_threshold, item.approved_by, item.approved_at or ""]
        for item in methodology_snapshots
    ])

    copied = []
    for document in documents:
        if not document.stored_name:
            continue
        if storage.exists(document.stored_name):
            destination = evidence_dir / f"{document.id}_{Path(document.name).name}"
            destination.write_bytes(storage.get_bytes(document.stored_name))
            copied.append(str(destination.relative_to(work)))
    for response in supplier_responses:
        if not response.evidence_stored_name:
            continue
        if storage.exists(response.evidence_stored_name):
            destination = evidence_dir / f"proveedor_{response.id}_{Path(response.evidence_name).name}"
            destination.write_bytes(storage.get_bytes(response.evidence_stored_name))
            copied.append(str(destination.relative_to(work)))
    for report in reports:
        if storage.exists(report.stored_name):
            destination = reports_dir / f"{report.id}_{Path(report.file_name).name}"
            destination.write_bytes(storage.get_bytes(report.stored_name))
            copied.append(str(destination.relative_to(work)))

    manifest = {
        "producto": "Calcula tu Huella",
        "version_aplicacion": settings.version,
        "inventario": {"id": inventory.id, "nombre": inventory.name, "version": inventory.version, "estado": inventory.status},
        "organizacion": inventory.organization.name,
        "periodo": [str(inventory.start_date), str(inventory.end_date)],
        "metodologia": inventory.methodology_version,
        "gwp": inventory.gwp_version,
        "generado_por": generated_by,
        "generado_en": datetime.now(UTC).isoformat(),
        "conteos": {
            "fuentes": len(sources), "datos": len(records), "calculos": len(calculations), "factores": len(factors),
            "evidencias": len(documents), "observaciones": len(observations), "hallazgos": len(findings), "informes": len(reports),
            "solicitudes_proveedores": len(supplier_requests), "respuestas_proveedores": len(supplier_responses),
            "controles_cumplimiento": len(compliance), "documentos_controlados": len(controlled_documents),
            "snapshots_metodologicos": len(methodology_snapshots),
        },
        "archivos_copiados": copied,
    }
    (work / "00_manifiesto.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    zip_name = f"paquete_verificacion_{inventory.id}_{stamp}.zip"
    zip_path = INSTANCE_DIR / zip_name
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(work.rglob("*")):
            if file.is_file():
                archive.write(file, file.relative_to(work))
    shutil.rmtree(work)
    zip_content = zip_path.read_bytes()
    digest = hashlib.sha256(zip_content).hexdigest()
    storage.put_bytes(zip_name, zip_content, "application/zip")
    artifact = ReportArtifact(
        inventory_id=inventory.id,
        report_type="Paquete de verificación",
        version=inventory.version,
        status="Generado",
        file_name=zip_name,
        stored_name=zip_name,
        file_size=zip_path.stat().st_size,
        sha256=digest,
        generated_by=generated_by,
    )
    session.add(artifact)
    session.flush()
    return artifact
