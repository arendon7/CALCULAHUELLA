from __future__ import annotations

import csv
import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .config import INSTANCE_DIR, settings
from .database import (
    ActivityData,
    ActivityIndicator,
    AppUser,
    DataRequest,
    DemoEnvironmentCertification,
    EmissionCalculation,
    EmissionFactor,
    EmissionFactorVersion,
    EmissionSource,
    EvidenceDocument,
    Facility,
    Inventory,
    InventoryFacility,
    Notification,
    NotificationPreference,
    Organization,
    OrganizationMembership,
    OrganizationCarbonProfile,
    DiagnosticAssessment,
    ImplementationPlan,
    PlatformSetting,
    ReductionAction,
    ReviewObservation,
    SourceFactorAssignment,
    SupportTicket,
    UPLOAD_DIR,
    add_audit,
    hash_password,
    refresh_progress,
)

DEMO_ORGANIZATIONS = ("Industrias Andinas", "Greenatics")
DEMO_CERT_DIR = INSTANCE_DIR / "certifications" / "demo"
DEMO_CERT_DIR.mkdir(parents=True, exist_ok=True)


def _canonical(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _get_factor_version(session: Session, factor_name: str) -> EmissionFactorVersion:
    version = session.scalar(
        select(EmissionFactorVersion)
        .join(EmissionFactor)
        .where(EmissionFactor.name == factor_name, EmissionFactorVersion.status == "Aprobado")
        .order_by(EmissionFactorVersion.id.desc())
        .limit(1)
    )
    if not version:
        raise ValueError(f"No existe el factor requerido para el demo: {factor_name}")
    return version


def _ensure_setting(session: Session, organization_id: int, key: str, value: str, description: str) -> None:
    item = session.scalar(select(PlatformSetting).where(
        PlatformSetting.organization_id == organization_id,
        PlatformSetting.key == key,
    ))
    if item:
        item.value = value
        item.description = description
        item.updated_by = "sistema-demo-v045"
    else:
        session.add(PlatformSetting(
            organization_id=organization_id,
            key=key,
            value=value,
            description=description,
            updated_by="sistema-demo-v045",
        ))


def _ensure_memberships(session: Session, organization_id: int) -> None:
    demo_users = list(session.scalars(select(AppUser).where(AppUser.email.like("%@calculatuhuella.local"))))
    for user in demo_users:
        membership = session.scalar(select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == organization_id,
        ))
        if not membership:
            session.add(OrganizationMembership(
                user_id=user.id,
                organization_id=organization_id,
                role=user.role,
                active=True,
            ))
        else:
            membership.active = True
            membership.role = user.role


def _ensure_notification(
    session: Session,
    organization_id: int,
    user: AppUser,
    title: str,
    message: str,
    link: str,
    category: str,
    priority: str = "Normal",
) -> None:
    exists = session.scalar(select(Notification).where(
        Notification.organization_id == organization_id,
        Notification.user_id == user.id,
        Notification.title == title,
    ))
    if not exists:
        session.add(Notification(
            organization_id=organization_id,
            user_id=user.id,
            title=title,
            message=message,
            link=link,
            category=category,
            priority=priority,
            status="Entregada",
            delivered_at=datetime.now(UTC),
        ))


def _ensure_support_ticket(
    session: Session,
    organization_id: int,
    subject: str,
    description: str,
    *,
    category: str = "Soporte funcional",
    priority: str = "Normal",
    status: str = "Abierto",
    resolution: str = "",
) -> None:
    ticket = session.scalar(select(SupportTicket).where(
        SupportTicket.organization_id == organization_id,
        SupportTicket.subject == subject,
    ))
    if not ticket:
        session.add(SupportTicket(
            organization_id=organization_id,
            created_by="cliente@calculatuhuella.local",
            category=category,
            priority=priority,
            status=status,
            subject=subject,
            description=description,
            assigned_to="Equipo Calcula tu Huella",
            resolution=resolution,
            closed_at=datetime.now(UTC) if status == "Cerrado" else None,
        ))


def _write_demo_csv(path: Path, rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerows(rows)


def _ensure_evidence_csv(
    session: Session,
    inventory: Inventory,
    source: EmissionSource,
    filename: str,
    document_type: str,
    period_label: str,
    rows: list[list[object]],
    status: str = "Aprobado",
) -> EvidenceDocument:
    existing = session.scalar(select(EvidenceDocument).where(
        EvidenceDocument.inventory_id == inventory.id,
        EvidenceDocument.name == filename,
    ))
    if existing:
        return existing
    directory = UPLOAD_DIR / f"org_{inventory.organization_id}" / f"inventory_{inventory.id}" / "demo_v044"
    path = directory / filename
    _write_demo_csv(path, rows)
    content = path.read_bytes()
    evidence = EvidenceDocument(
        inventory_id=inventory.id,
        source_id=source.id,
        name=filename,
        stored_name=str(path.relative_to(INSTANCE_DIR)),
        document_type=document_type,
        source_name=source.name,
        period_label=period_label,
        status=status,
        uploaded_by="sistema-demo-v045",
        file_size=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        notes="Archivo sintético de demostración. No constituye soporte real de Greenatics.",
    )
    session.add(evidence)
    session.flush()
    return evidence


def _ensure_activity_series(
    session: Session,
    source: EmissionSource,
    values: list[float],
    unit: str,
    *,
    evidence: EvidenceDocument | None = None,
    estimated_from_month: int = 9,
    origin: str = "Registro operativo",
) -> None:
    existing_months = set(session.scalars(select(ActivityData.period_start).where(ActivityData.source_id == source.id)))
    for month, value in enumerate(values, 1):
        period = date(2026, month, 1)
        if period in existing_months:
            continue
        estimated = month >= estimated_from_month
        session.add(ActivityData(
            source_id=source.id,
            evidence_id=evidence.id if evidence and not estimated else None,
            period_start=period,
            period_end=date(2026, month, 28),
            value=float(value),
            unit=unit,
            data_origin="Estimación" if estimated else origin,
            quality_level="C" if estimated else "B",
            is_estimated=estimated,
            uncertainty_percentage=20 if estimated else 7,
            uncertainty_basis="Proyección demostrativa" if estimated else "Consolidado operativo sintético",
            status="Provisional" if estimated else "Aprobado",
            notes="Dato sintético V0.45 para demostración; no representa información contable u operativa real.",
            created_by="sistema-demo-v045",
        ))


def _ensure_factor_assignments(session: Session, source: EmissionSource, factor_names: list[str]) -> None:
    existing_ids = set(session.scalars(select(SourceFactorAssignment.factor_version_id).where(
        SourceFactorAssignment.source_id == source.id,
        SourceFactorAssignment.active.is_(True),
    )))
    for factor_name in factor_names:
        version = _get_factor_version(session, factor_name)
        if version.id not in existing_ids:
            session.add(SourceFactorAssignment(
                source_id=source.id,
                factor_version_id=version.id,
                active=True,
                assigned_by="sistema-demo-v045",
                notes="Asignación de ejemplo certificada para entorno demostrativo V0.45.",
            ))


def _ensure_request(
    session: Session,
    inventory: Inventory,
    source: EmissionSource | None,
    title: str,
    requested_to: str,
    due_date: date,
    status: str,
    instructions: str,
) -> None:
    existing = session.scalar(select(DataRequest).where(
        DataRequest.inventory_id == inventory.id,
        DataRequest.title == title,
    ))
    if not existing:
        session.add(DataRequest(
            inventory_id=inventory.id,
            source_id=source.id if source else None,
            title=title,
            source_name=source.name if source else "Inventario",
            requested_to=requested_to,
            due_date=due_date,
            status=status,
            instructions=instructions,
            completed_at=datetime.now(UTC) if status in {"Completada", "Cerrada"} else None,
        ))


def _ensure_observation(
    session: Session,
    inventory: Inventory,
    source: EmissionSource | None,
    title: str,
    description: str,
    severity: str,
    status: str,
    assigned_to: str,
) -> None:
    existing = session.scalar(select(ReviewObservation).where(
        ReviewObservation.inventory_id == inventory.id,
        ReviewObservation.title == title,
    ))
    if not existing:
        closed = status == "Cerrada"
        session.add(ReviewObservation(
            inventory_id=inventory.id,
            source_id=source.id if source else None,
            entity_type="Fuente" if source else "Inventario",
            entity_label=source.name if source else inventory.name,
            title=title,
            description=description,
            severity=severity,
            status=status,
            assigned_to=assigned_to,
            due_date=date(2026, 9, 15) if not closed else None,
            created_by="revisor@calculatuhuella.local",
            response="Respuesta demostrativa documentada." if status in {"En corrección", "Cerrada"} else "",
            responded_by="cliente@calculatuhuella.local" if status in {"En corrección", "Cerrada"} else "",
            responded_at=datetime.now(UTC) if status in {"En corrección", "Cerrada"} else None,
            resolution="Validación demostrativa completada." if closed else "",
            resolved_by="revisor@calculatuhuella.local" if closed else "",
            resolved_at=datetime.now(UTC) if closed else None,
            closed_by="revisor@calculatuhuella.local" if closed else "",
            closed_at=datetime.now(UTC) if closed else None,
        ))


def _ensure_greenatics(session: Session) -> Organization:
    organization = session.scalar(select(Organization).where(Organization.trade_name == "Greenatics"))
    if not organization:
        organization = Organization(
            name="GREENATICS S.A.S. · Demo",
            trade_name="Greenatics",
            tax_id="901.000.444-DEMO",
            sector="Gestión de residuos y fertilizantes",
            ciiu_code="E3821",
            country="Colombia",
            department="Antioquia",
            city="Medellín",
            employees=32,
            annual_revenue=4_800_000_000,
            contact_name="Equipo ambiental Greenatics",
            contact_email="ambiental@greenatics.demo",
            status="Activa",
        )
        session.add(organization)
        session.flush()
    _ensure_setting(session, organization.id, "demo_dataset", "true", "Organización con datos sintéticos V0.45")
    _ensure_setting(session, organization.id, "demo_disclaimer", "Todos los datos son de ejemplo", "Aviso obligatorio del entorno demo")
    _ensure_memberships(session, organization.id)

    facilities_by_name = {item.name: item for item in session.scalars(select(Facility).where(Facility.organization_id == organization.id))}
    facility_specs = [
        ("Planta Yarumal", "Planta de aprovechamiento", "Yarumal", "Zona industrial municipal", 12),
        ("Planta Támesis", "Planta de aprovechamiento", "Támesis", "Zona rural", 11),
        ("Oficina Medellín", "Oficina administrativa", "Medellín", "Laureles", 9),
    ]
    for name, facility_type, city, address, employees in facility_specs:
        if name not in facilities_by_name:
            item = Facility(
                organization_id=organization.id,
                name=name,
                facility_type=facility_type,
                city=city,
                address=address,
                employees=employees,
                operational_control=True,
            )
            session.add(item)
            session.flush()
            facilities_by_name[name] = item

    inventory = session.scalar(select(Inventory).where(
        Inventory.organization_id == organization.id,
        Inventory.name == "Inventario corporativo Greenatics 2026 · Demo",
    ))
    if not inventory:
        inventory = Inventory(
            organization_id=organization.id,
            name="Inventario corporativo Greenatics 2026 · Demo",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            objective="Demostrar la gestión mensual de emisiones de plantas de residuos, fertilizantes y operación corporativa.",
            base_year=2026,
            methodology="GHG Protocol + ISO 14064-1",
            methodology_version="GHG Protocol Corporate Standard · ISO 14064-1:2018",
            gwp_version="IPCC AR6 · 100 años",
            consolidation_approach="Control operacional",
            materiality_threshold=5,
            status="En revisión",
            progress=0,
            current_stage="Recolección",
            notes="ENTORNO DEMOSTRATIVO. Datos sintéticos para visualizar flujos; no corresponden al inventario oficial de Greenatics.",
            version="0.45",
        )
        session.add(inventory)
        session.flush()
    else:
        inventory.version = "0.45"
        if "ENTORNO DEMOSTRATIVO" not in inventory.notes:
            inventory.notes = "ENTORNO DEMOSTRATIVO. " + inventory.notes

    linked = set(session.scalars(select(InventoryFacility.facility_id).where(InventoryFacility.inventory_id == inventory.id)))
    for facility in facilities_by_name.values():
        if facility.id not in linked:
            session.add(InventoryFacility(inventory_id=inventory.id, facility_id=facility.id, included=True, inclusion_percentage=100))

    source_specs = [
        ("Electricidad Yarumal", facilities_by_name["Planta Yarumal"], 2, "Energía adquirida", "Administración Yarumal", "kWh", "location-based", ["Electricidad SIN Colombia · inventarios 2024"]),
        ("Electricidad Támesis", facilities_by_name["Planta Támesis"], 2, "Energía adquirida", "Administración Támesis", "kWh", "location-based", ["Electricidad SIN Colombia · inventarios 2024"]),
        ("Diésel de maquinaria Yarumal", facilities_by_name["Planta Yarumal"], 1, "Combustión móvil", "Operaciones Yarumal", "gal", "No aplica", ["Diésel B10 Colombia · CO2 FECOC transcrito"]),
        ("Gasolina logística", facilities_by_name["Oficina Medellín"], 1, "Combustión móvil", "Logística", "gal", "No aplica", ["Gasolina E10 Colombia · CO2 FECOC transcrito"]),
        ("Compostaje Yarumal", facilities_by_name["Planta Yarumal"], 1, "Tratamiento propio de residuos", "Jefatura de planta", "t", "No aplica", ["Compostaje de residuos orgánicos húmedos · CH4 Tier 1", "Compostaje de residuos orgánicos húmedos · N2O Tier 1"]),
        ("Compostaje Támesis", facilities_by_name["Planta Támesis"], 1, "Tratamiento propio de residuos", "Jefatura de planta", "t", "No aplica", ["Compostaje de residuos orgánicos húmedos · CH4 Tier 1", "Compostaje de residuos orgánicos húmedos · N2O Tier 1"]),
        ("Digestión anaerobia Támesis", facilities_by_name["Planta Támesis"], 1, "Tratamiento propio de residuos", "Operaciones Támesis", "t", "No aplica", ["Digestión anaerobia en instalación de biogás · CH4 Tier 1"]),
        ("Transporte contratado", None, 3, "Transporte y distribución", "Logística", "t·km", "No aplica", ["Transporte de carga · demo"]),
        ("Rechazos enviados a disposición", facilities_by_name["Planta Yarumal"], 3, "Residuos operacionales", "Gestión ambiental", "t", "No aplica", ["Residuos gestionados · demo"]),
    ]
    sources_by_name = {item.name: item for item in session.scalars(select(EmissionSource).where(EmissionSource.inventory_id == inventory.id))}
    for name, facility, scope, category, responsible, unit, scope2_method, factors in source_specs:
        source = sources_by_name.get(name)
        if not source:
            source = EmissionSource(
                inventory_id=inventory.id,
                facility_id=facility.id if facility else None,
                name=name,
                scope=scope,
                category=category,
                responsible=responsible,
                materiality="Alta" if scope in {1, 2} else "Media",
                data_frequency="Mensual",
                preferred_unit=unit,
                scope2_method=scope2_method,
                icon="activity",
            )
            session.add(source)
            session.flush()
            sources_by_name[name] = source
        _ensure_factor_assignments(session, source, factors)

    electricity_rows = [["Mes", "Yarumal kWh", "Támesis kWh"]] + [
        [month, y, t] for month, (y, t) in enumerate(zip(
            [3420, 3580, 3710, 3650, 3890, 4120, 4050, 4180, 4290, 4410, 4370, 4520],
            [2870, 3010, 3150, 3220, 3380, 3510, 3660, 3740, 3860, 3990, 4070, 4210],
        ), 1)
    ]
    energy_evidence = _ensure_evidence_csv(
        session, inventory, sources_by_name["Electricidad Yarumal"],
        "greenatics_energia_2026_demo.csv", "Factura consolidada", "Enero–agosto 2026", electricity_rows,
    )
    residues_rows = [["Mes", "Compostaje Yarumal t", "Compostaje Támesis t", "Digestión Támesis t"]] + [
        [month, a, b, c] for month, (a, b, c) in enumerate(zip(
            [8.4, 9.1, 10.5, 11.2, 12.8, 13.6, 14.1, 14.8, 15.2, 15.7, 16.1, 16.5],
            [5.2, 5.8, 6.4, 7.1, 7.9, 8.5, 9.2, 9.8, 10.4, 10.9, 11.3, 11.8],
            [2.0, 2.4, 2.9, 3.3, 3.8, 4.2, 4.7, 5.1, 5.6, 6.0, 6.4, 6.8],
        ), 1)
    ]
    residues_evidence = _ensure_evidence_csv(
        session, inventory, sources_by_name["Compostaje Yarumal"],
        "greenatics_tratamiento_residuos_2026_demo.csv", "Bitácora de planta", "Enero–agosto 2026", residues_rows,
    )

    series = {
        "Electricidad Yarumal": ([3420, 3580, 3710, 3650, 3890, 4120, 4050, 4180, 4290, 4410, 4370, 4520], "kWh", energy_evidence),
        "Electricidad Támesis": ([2870, 3010, 3150, 3220, 3380, 3510, 3660, 3740, 3860, 3990, 4070, 4210], "kWh", energy_evidence),
        "Diésel de maquinaria Yarumal": ([112, 118, 121, 116, 126, 132, 129, 135, 139, 142, 145, 149], "gal", None),
        "Gasolina logística": ([72, 76, 79, 75, 82, 86, 84, 88, 91, 94, 96, 99], "gal", None),
        "Compostaje Yarumal": ([8.4, 9.1, 10.5, 11.2, 12.8, 13.6, 14.1, 14.8, 15.2, 15.7, 16.1, 16.5], "t", residues_evidence),
        "Compostaje Támesis": ([5.2, 5.8, 6.4, 7.1, 7.9, 8.5, 9.2, 9.8, 10.4, 10.9, 11.3, 11.8], "t", residues_evidence),
        "Digestión anaerobia Támesis": ([2.0, 2.4, 2.9, 3.3, 3.8, 4.2, 4.7, 5.1, 5.6, 6.0, 6.4, 6.8], "t", residues_evidence),
        "Transporte contratado": ([1850, 1920, 2050, 2140, 2260, 2380, 2450, 2520, 2600, 2710, 2790, 2880], "t·km", None),
        "Rechazos enviados a disposición": ([1.2, 1.1, 1.0, 0.9, 0.9, 0.8, 0.8, 0.7, 0.7, 0.7, 0.6, 0.6], "t", None),
    }
    for source_name, (values, unit, evidence) in series.items():
        _ensure_activity_series(session, sources_by_name[source_name], values, unit, evidence=evidence)

    if not session.scalar(select(ActivityIndicator).where(
        ActivityIndicator.inventory_id == inventory.id,
        ActivityIndicator.indicator_type == "Residuos orgánicos recibidos",
    )):
        for month, value in enumerate([19.4, 21.1, 23.2, 25.0, 27.6, 29.8, 31.5, 32.7, 34.0, 35.2, 36.1, 37.3], 1):
            session.add(ActivityIndicator(
                inventory_id=inventory.id,
                period_start=date(2026, month, 1),
                period_end=date(2026, month, 28),
                indicator_type="Residuos orgánicos recibidos",
                value=value,
                unit="t",
                source_name="Bitácora demostrativa de recepción",
                status="Provisional" if month >= 9 else "Aprobado",
                created_by="sistema-demo-v045",
            ))

    _ensure_request(session, inventory, sources_by_name["Transporte contratado"], "Completar manifiestos de transporte septiembre–diciembre", "Logística", date(2026, 9, 20), "Pendiente", "Adjuntar rutas, toneladas y distancias. Los valores actuales son proyecciones demo.")
    _ensure_request(session, inventory, sources_by_name["Digestión anaerobia Támesis"], "Validar medición de biogás y fugas", "Operaciones Támesis", date(2026, 9, 12), "En revisión", "Confirmar el balance de masa y documentar la eficiencia de captura.")
    _ensure_request(session, inventory, sources_by_name["Electricidad Yarumal"], "Conciliar facturas de energía enero–agosto", "Administración Yarumal", date(2026, 8, 30), "Completada", "Verificar correspondencia entre factura y registro mensual.")
    _ensure_request(session, inventory, sources_by_name["Rechazos enviados a disposición"], "Adjuntar certificados de disposición final", "Gestión ambiental", date(2026, 9, 18), "Pendiente", "Cargar certificados del gestor y peso por mes.")

    _ensure_observation(session, inventory, sources_by_name["Transporte contratado"], "Datos proyectados pendientes de soporte", "Los meses septiembre–diciembre son estimados y deben sustituirse antes del cierre.", "Mayor", "Abierta", "Logística")
    _ensure_observation(session, inventory, sources_by_name["Digestión anaerobia Támesis"], "Revisar frontera de fugas de biogás", "Confirmar si el factor aplicado cubre únicamente tratamiento o también pérdidas no capturadas.", "Mayor", "En corrección", "Operaciones Támesis")
    _ensure_observation(session, inventory, sources_by_name["Electricidad Yarumal"], "Muestra factura-periodo verificada", "La muestra documental sintética coincide con el consolidado cargado.", "Informativa", "Cerrada", "Administración Yarumal")

    if not session.scalar(select(ReductionAction).where(
        ReductionAction.inventory_id == inventory.id,
        ReductionAction.title == "Optimización energética de las plantas",
    )):
        session.add_all([
            ReductionAction(
                inventory_id=inventory.id,
                source_id=sources_by_name["Electricidad Yarumal"].id,
                title="Optimización energética de las plantas",
                description="Medición por proceso, motores eficientes y programación de operación.",
                expected_reduction=6.8,
                investment_cost=42_000_000,
                annual_savings=24_000_000,
                priority="Alta",
                responsible="Dirección de operaciones",
                target_date=date(2027, 6, 30),
                status="En evaluación",
                progress_percent=30,
                created_by="consultor@calculatuhuella.local",
            ),
            ReductionAction(
                inventory_id=inventory.id,
                source_id=sources_by_name["Digestión anaerobia Támesis"].id,
                title="Mejorar captura y uso del biogás",
                description="Instrumentar producción, controlar fugas y evaluar aprovechamiento térmico.",
                expected_reduction=12.5,
                investment_cost=68_000_000,
                annual_savings=31_000_000,
                priority="Alta",
                responsible="Operaciones Támesis",
                target_date=date(2027, 12, 31),
                status="Diseño",
                progress_percent=20,
                created_by="consultor@calculatuhuella.local",
            ),
        ])

    demo_users = {user.role: user for user in session.scalars(select(AppUser).where(AppUser.email.like("%@calculatuhuella.local")))}
    if demo_users.get("Administrador"):
        _ensure_notification(session, organization.id, demo_users["Administrador"], "Greenatics demo lista para explorar", "La organización contiene plantas, inventario, datos mensuales, solicitudes, hallazgos y acciones de reducción de ejemplo.", "/dashboard", "Demo", "Alta")
    if demo_users.get("Consultor"):
        _ensure_notification(session, organization.id, demo_users["Consultor"], "Conciliación metodológica pendiente", "Revisa el tratamiento de digestión anaerobia y los meses proyectados antes del cierre demo.", "/control", "Revisión", "Alta")
    if demo_users.get("Cliente"):
        _ensure_notification(session, organization.id, demo_users["Cliente"], "Tienes 2 solicitudes pendientes", "Completa transporte contratado y certificados de disposición para mejorar la cobertura del inventario.", "/informacion", "Solicitud", "Alta")
    if demo_users.get("Revisor"):
        _ensure_notification(session, organization.id, demo_users["Revisor"], "Hallazgos Greenatics disponibles", "El inventario demo contiene hallazgos abiertos, en corrección y cerrados para probar el flujo de revisión.", "/control", "Revisión", "Normal")

    _ensure_support_ticket(session, organization.id, "¿Cómo reemplazo una proyección por un dato real?", "Consulta demostrativa sobre la sustitución de registros estimados y conservación de trazabilidad.", priority="Normal", status="Cerrado", resolution="Editar el registro o cargar el archivo operativo; la auditoría conservará el cambio.")
    _ensure_support_ticket(session, organization.id, "Revisión del factor de digestión anaerobia", "Solicitud demostrativa de acompañamiento metodológico para confirmar frontera y factor.", category="Metodología", priority="Alta", status="Abierto")

    session.flush()
    refresh_progress(session, inventory)
    from .calculations import recalculate_inventory
    recalculate_inventory(session, inventory)
    add_audit(session, organization.id, "sistema-demo-v045", "PREPARAR", "Entorno demostrativo", "Greenatics", "Datos sintéticos, mensajes, solicitudes, evidencias y resultados V0.45")
    return organization


def _enrich_andinas(session: Session) -> Organization:
    organization = session.scalar(select(Organization).where(Organization.trade_name == "Industrias Andinas"))
    if not organization:
        organization = Organization(
            name="Industrias Andinas Demo S.A.S.",
            trade_name="Industrias Andinas",
            tax_id="901.555.101-8",
            sector="Manufactura",
            ciiu_code="C2029",
            country="Colombia",
            department="Antioquia",
            city="Medellín",
            employees=186,
            annual_revenue=18_500_000_000,
            contact_name="Ana Martínez",
            contact_email="ambiental@industriasandinas.demo",
            status="Activa",
        )
        session.add(organization)
        session.flush()
    demo_users = list(session.scalars(select(AppUser).where(AppUser.email.like("%@calculatuhuella.local"))))
    if not demo_users:
        demo_password = hash_password("Demo2026!")
        specs = [
            ("admin@calculatuhuella.local", "Laura Méndez", "Administrador"),
            ("consultor@calculatuhuella.local", "Carlos Uribe", "Consultor"),
            ("cliente@calculatuhuella.local", "Ana Martínez", "Cliente"),
            ("revisor@calculatuhuella.local", "María Fernández", "Revisor"),
            ("verificador@calculatuhuella.local", "Andrés Salazar", "Verificador"),
        ]
        for email, name, role in specs:
            user = AppUser(organization_id=organization.id, email=email, name=name, role=role, password_hash=demo_password, active=True)
            session.add(user)
            session.flush()
            session.add(NotificationPreference(user_id=user.id, in_app_enabled=True, email_enabled=True, digest_frequency="Inmediato"))
    _ensure_setting(session, organization.id, "demo_dataset", "true", "Organización con datos sintéticos V0.45")
    _ensure_setting(session, organization.id, "demo_disclaimer", "Todos los datos son de ejemplo", "Aviso obligatorio del entorno demo")
    _ensure_memberships(session, organization.id)
    inventory = session.scalar(select(Inventory).where(Inventory.organization_id == organization.id).order_by(Inventory.start_date.desc()).limit(1))
    if inventory:
        inventory.version = "0.45"
        _ensure_request(session, inventory, None, "Aprobar cierre ejecutivo demo", "Dirección ambiental", date(2026, 9, 30), "Pendiente", "Revisar hallazgos mayores y autorizar la emisión del informe demostrativo.")
    users = {user.role: user for user in session.scalars(select(AppUser).where(AppUser.email.like("%@calculatuhuella.local")))}
    if users.get("Administrador"):
        _ensure_notification(session, organization.id, users["Administrador"], "Andinas demo enriquecida", "La empresa incluye inventarios, solicitudes, mensajes, soporte, proveedores, escenarios y riesgos climáticos para recorrer la plataforma.", "/dashboard", "Demo", "Alta")
    if users.get("Cliente"):
        _ensure_notification(session, organization.id, users["Cliente"], "Solicitud de cierre ejecutivo", "La dirección ambiental debe revisar los hallazgos y aprobar el informe demostrativo.", "/informacion", "Solicitud", "Normal")
    _ensure_support_ticket(session, organization.id, "No veo el avance del transporte contratado", "Ticket demostrativo para revisar cobertura, evidencias y cálculo de una fuente incompleta.", priority="Alta", status="Abierto")
    _ensure_support_ticket(session, organization.id, "Informe ejecutivo generado correctamente", "Caso resuelto de ejemplo para mostrar el historial de soporte.", status="Cerrado", resolution="Se regeneró el informe después de completar el recálculo.")
    add_audit(session, organization.id, "sistema-demo-v045", "ACTUALIZAR", "Entorno demostrativo", "Industrias Andinas", "Mensajes, solicitud ejecutiva y tickets demo V0.45")
    return organization


def ensure_demo_environment(session: Session) -> dict[str, object]:
    if not settings.seed_demo:
        raise ValueError("El entorno demostrativo está desactivado. Configura SEED_DEMO=true solo fuera de producción.")
    andinas = _enrich_andinas(session)
    greenatics = _ensure_greenatics(session)
    from .services.product_intelligence import ensure_demo_product_intelligence
    ensure_demo_product_intelligence(session)
    session.flush()
    return {
        "organizations": [andinas.id, greenatics.id],
        "summary": demo_environment_summary(session),
    }


def _org_summary(session: Session, organization: Organization) -> dict[str, object]:
    inventories = list(session.scalars(select(Inventory).where(Inventory.organization_id == organization.id)))
    inventory_ids = [item.id for item in inventories]
    source_ids: list[int] = []
    if inventory_ids:
        source_ids = list(session.scalars(select(EmissionSource.id).where(EmissionSource.inventory_id.in_(inventory_ids))))
    profile = session.scalar(select(OrganizationCarbonProfile).where(OrganizationCarbonProfile.organization_id == organization.id))
    assessment = session.scalar(
        select(DiagnosticAssessment)
        .where(DiagnosticAssessment.organization_id == organization.id)
        .order_by(DiagnosticAssessment.assessed_at.desc(), DiagnosticAssessment.id.desc())
        .limit(1)
    )
    plan_count = session.scalar(select(func.count(ImplementationPlan.id)).where(ImplementationPlan.organization_id == organization.id)) or 0
    return {
        "id": organization.id,
        "name": organization.name,
        "trade_name": organization.trade_name,
        "sector": organization.sector,
        "facilities": session.scalar(select(func.count(Facility.id)).where(Facility.organization_id == organization.id)) or 0,
        "inventories": len(inventories),
        "sources": len(source_ids),
        "activity_records": session.scalar(select(func.count(ActivityData.id)).where(ActivityData.source_id.in_(source_ids))) if source_ids else 0,
        "calculations": session.scalar(select(func.count(EmissionCalculation.id)).join(ActivityData).where(ActivityData.source_id.in_(source_ids))) if source_ids else 0,
        "evidence": session.scalar(select(func.count(EvidenceDocument.id)).where(EvidenceDocument.inventory_id.in_(inventory_ids))) if inventory_ids else 0,
        "requests": session.scalar(select(func.count(DataRequest.id)).where(DataRequest.inventory_id.in_(inventory_ids))) if inventory_ids else 0,
        "observations": session.scalar(select(func.count(ReviewObservation.id)).where(ReviewObservation.inventory_id.in_(inventory_ids))) if inventory_ids else 0,
        "notifications": session.scalar(select(func.count(Notification.id)).where(Notification.organization_id == organization.id)) or 0,
        "support_tickets": session.scalar(select(func.count(SupportTicket.id)).where(SupportTicket.organization_id == organization.id)) or 0,
        "pending_requests": session.scalar(select(func.count(DataRequest.id)).where(DataRequest.inventory_id.in_(inventory_ids), DataRequest.status.notin_(["Completada", "Cerrada"]))) if inventory_ids else 0,
        "open_observations": session.scalar(select(func.count(ReviewObservation.id)).where(ReviewObservation.inventory_id.in_(inventory_ids), ReviewObservation.status.notin_(["Cerrada", "Resuelta"]))) if inventory_ids else 0,
        "profile_completion": profile.profile_completion if profile else 0,
        "maturity_level": assessment.maturity_level if assessment else "Sin diagnóstico",
        "complexity_level": assessment.complexity_level if assessment else "Sin diagnóstico",
        "recommended_package": assessment.recommended_package_code if assessment else "",
        "assessment_status": assessment.status if assessment else "Pendiente",
        "implementation_plans": int(plan_count),
        "total_emissions": round(sum(float(source.emissions or 0) for source in session.scalars(select(EmissionSource).where(EmissionSource.inventory_id.in_(inventory_ids)))) if inventory_ids else 0, 3),
    }


def demo_environment_summary(session: Session) -> dict[str, object]:
    organizations = list(session.scalars(select(Organization).where(Organization.trade_name.in_(DEMO_ORGANIZATIONS)).order_by(Organization.trade_name)))
    rows = [_org_summary(session, organization) for organization in organizations]
    certifications = list(session.scalars(select(DemoEnvironmentCertification).order_by(DemoEnvironmentCertification.created_at.desc()).limit(10)))
    return {
        "version": settings.version,
        "enabled": settings.seed_demo,
        "organizations": rows,
        "organization_count": len(rows),
        "totals": {
            key: sum(int(row.get(key, 0) or 0) for row in rows)
            for key in ("facilities", "inventories", "sources", "activity_records", "calculations", "evidence", "requests", "observations", "notifications", "support_tickets", "implementation_plans")
        },
        "certifications": certifications,
    }


def certify_demo_environment(
    session: Session,
    organization_id: int,
    performed_by: str,
    notes: str = "",
) -> DemoEnvironmentCertification:
    ensure_demo_environment(session)
    session.flush()
    summary = demo_environment_summary(session)
    by_name = {row["trade_name"]: row for row in summary["organizations"]}
    greenatics = by_name.get("Greenatics", {})
    andinas = by_name.get("Industrias Andinas", {})
    greenatics_org = session.scalar(select(Organization).where(Organization.trade_name == "Greenatics").options(selectinload(Organization.facilities)))
    andinas_org = session.scalar(select(Organization).where(Organization.trade_name == "Industrias Andinas").options(selectinload(Organization.facilities)))
    greenatics_sites = {item.name for item in greenatics_org.facilities} if greenatics_org else set()
    andinas_sites = {item.name for item in andinas_org.facilities} if andinas_org else set()
    checks = [
        {"code": "two_companies", "label": "Greenatics y Andinas disponibles", "ok": summary["organization_count"] == 2, "critical": True, "detail": f"{summary['organization_count']} organizaciones demo"},
        {"code": "greenatics_sites", "label": "Sedes Greenatics", "ok": {"Planta Yarumal", "Planta Támesis"}.issubset(greenatics_sites), "critical": True, "detail": ", ".join(sorted(greenatics_sites))},
        {"code": "andinas_sites", "label": "Sedes Andinas", "ok": {"Planta Medellín", "Bodega Rionegro"}.issubset(andinas_sites), "critical": True, "detail": ", ".join(sorted(andinas_sites))},
        {"code": "activity", "label": "Datos de actividad", "ok": int(greenatics.get("activity_records", 0)) >= 60 and int(andinas.get("activity_records", 0)) >= 20, "critical": True, "detail": f"Greenatics {greenatics.get('activity_records', 0)} / Andinas {andinas.get('activity_records', 0)}"},
        {"code": "calculations", "label": "Cálculos reproducibles", "ok": int(greenatics.get("calculations", 0)) > 0 and int(andinas.get("calculations", 0)) > 0, "critical": True, "detail": f"Greenatics {greenatics.get('calculations', 0)} / Andinas {andinas.get('calculations', 0)}"},
        {"code": "workflow", "label": "Solicitudes, mensajes y revisión", "ok": all(int(row.get("requests", 0)) >= 3 and int(row.get("notifications", 0)) >= 2 and int(row.get("observations", 0)) >= 2 for row in (greenatics, andinas)), "critical": True, "detail": "Cada empresa debe mostrar solicitudes, notificaciones y observaciones."},
        {"code": "evidence", "label": "Evidencias descargables", "ok": int(greenatics.get("evidence", 0)) >= 2 and int(andinas.get("evidence", 0)) >= 2, "critical": True, "detail": f"Greenatics {greenatics.get('evidence', 0)} / Andinas {andinas.get('evidence', 0)}"},
        {"code": "support", "label": "Casos de soporte", "ok": int(greenatics.get("support_tickets", 0)) >= 2 and int(andinas.get("support_tickets", 0)) >= 2, "critical": False, "detail": "Incluye casos abiertos y resueltos."},
        {"code": "profiles", "label": "Perfil integral de empresa", "ok": all(int(row.get("profile_completion", 0)) >= 80 for row in (greenatics, andinas)), "critical": True, "detail": f"Greenatics {greenatics.get('profile_completion', 0)}% / Andinas {andinas.get('profile_completion', 0)}%"},
        {"code": "diagnostics", "label": "Diagnóstico de madurez y complejidad", "ok": all(row.get("assessment_status") == "Aprobado" for row in (greenatics, andinas)), "critical": True, "detail": f"Greenatics {greenatics.get('maturity_level', '')} / Andinas {andinas.get('maturity_level', '')}"},
        {"code": "implementation_plans", "label": "Plan de implementación por fases", "ok": all(int(row.get("implementation_plans", 0)) >= 1 for row in (greenatics, andinas)), "critical": True, "detail": f"Greenatics {greenatics.get('implementation_plans', 0)} / Andinas {andinas.get('implementation_plans', 0)}"},
        {"code": "demo_mode", "label": "Marcación demostrativa", "ok": settings.seed_demo and not settings.is_production, "critical": True, "detail": f"SEED_DEMO={settings.seed_demo}; APP_ENV={settings.environment}"},
    ]
    blockers = [item for item in checks if item["critical"] and not item["ok"]]
    status = "Certificado demo" if not blockers else "Bloqueado"
    payload = {
        "application": settings.app_name,
        "version": settings.version,
        "status": status,
        "performed_by": performed_by,
        "created_at": datetime.now(UTC).isoformat(),
        "summary": {"organizations": summary["organizations"], "totals": summary["totals"]},
        "checks": checks,
        "blockers": blockers,
        "disclaimer": "Todos los valores son sintéticos y solo demuestran el funcionamiento de la plataforma.",
    }
    certificate_hash = hashlib.sha256(_canonical(payload)).hexdigest()
    payload["certificate_hash"] = certificate_hash
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    artifact = DEMO_CERT_DIR / f"entorno_demo_v{settings.version.replace('.', '_')}_{timestamp}.json"
    artifact.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")
    row = DemoEnvironmentCertification(
        organization_id=organization_id,
        application_version=settings.version,
        status=status,
        certificate_hash=certificate_hash,
        artifact_name=artifact.name,
        artifact_sha256=_sha256_file(artifact),
        summary_json=json.dumps({"organizations": summary["organizations"], "totals": summary["totals"]}, ensure_ascii=False, sort_keys=True, default=str),
        checks_json=json.dumps(checks, ensure_ascii=False, sort_keys=True),
        notes=notes.strip(),
        performed_by=performed_by,
    )
    session.add(row)
    add_audit(session, organization_id, performed_by, "CERTIFICAR", "Entorno demostrativo", f"V{settings.version}", detail=status, new_value=certificate_hash)
    session.flush()
    return row


def resolve_demo_certificate(name: str) -> Path:
    candidate = (DEMO_CERT_DIR / Path(name).name).resolve()
    if candidate.parent != DEMO_CERT_DIR.resolve() or not candidate.is_file():
        raise FileNotFoundError(name)
    return candidate
