from __future__ import annotations

import hashlib
import json
import math
import secrets
from datetime import UTC, date, datetime
from typing import Generator

from openpyxl import Workbook
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .config import INSTANCE_DIR, PROJECT_DIR, settings
from .db.base import Base, DB_PATH, ENGINE, SessionLocal, UPLOAD_DIR
from .db.models import *  # noqa: F401,F403 - compatibility facade for existing modules
from .security import get_request_id, hash_password as secure_hash_password

def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session


def audit_event_digest(event: AuditEvent, previous_hash: str | None = None) -> str:
    created_at = event.created_at
    if created_at and created_at.tzinfo is not None:
        created_at = created_at.astimezone(UTC).replace(tzinfo=None)
    created = created_at.isoformat(timespec="microseconds") if created_at else ""
    values = [
        str(event.organization_id), event.user_email, event.action, event.entity_type,
        event.entity_label, event.detail or "", event.previous_value or "",
        event.new_value or "", event.reason or "", event.request_id or "",
        created, previous_hash if previous_hash is not None else (event.previous_hash or ""),
    ]
    return hashlib.sha256("\x1f".join(values).encode("utf-8")).hexdigest()


def backfill_audit_chain(session: Session) -> int:
    updated = 0
    organization_ids = list(session.scalars(select(AuditEvent.organization_id).distinct()))
    for organization_id in organization_ids:
        previous_hash = ""
        events = list(session.scalars(
            select(AuditEvent)
            .where(AuditEvent.organization_id == organization_id)
            .order_by(AuditEvent.id)
        ))
        for event in events:
            expected = audit_event_digest(event, previous_hash)
            # Backfill only legacy rows. Existing hashes are never rewritten here,
            # so a later modification remains detectable instead of being repaired.
            if not event.event_hash:
                event.previous_hash = previous_hash
                event.event_hash = expected
                updated += 1
            previous_hash = event.event_hash or expected
    return updated


def add_audit(
    session: Session,
    organization_id: int,
    user_email: str,
    action: str,
    entity_type: str,
    entity_label: str,
    detail: str = "",
    previous_value: str = "",
    new_value: str = "",
    reason: str = "",
) -> None:
    session.flush()
    previous = session.scalar(
        select(AuditEvent)
        .where(AuditEvent.organization_id == organization_id)
        .order_by(AuditEvent.id.desc())
        .limit(1)
    )
    created_at = datetime.now(UTC)
    event = AuditEvent(
        organization_id=organization_id,
        user_email=user_email,
        action=action,
        entity_type=entity_type,
        entity_label=entity_label,
        detail=detail,
        previous_value=previous_value,
        new_value=new_value,
        reason=reason,
        request_id=get_request_id(),
        previous_hash=previous.event_hash if previous and previous.event_hash else "",
        created_at=created_at,
    )
    event.event_hash = audit_event_digest(event)
    session.add(event)


def hash_password(password: str) -> str:
    return secure_hash_password(password)


def write_simple_pdf(path: Path, text: str) -> None:
    safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 50 760 Td ({safe}) Tj ET".encode("latin-1", errors="replace")
    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n",
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
        b"5 0 obj << /Length " + str(len(stream)).encode() + b" >> stream\n" + stream + b"\nendstream endobj\n",
    ]
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(data))
        data.extend(obj)
    xref = len(data)
    data.extend(f"xref\n0 {len(objects)+1}\n".encode())
    data.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    path.write_bytes(data)


def source_expected_periods(source: EmissionSource) -> int:
    if source.data_frequency.lower() == "anual":
        return 1
    if source.data_frequency.lower() == "trimestral":
        return 4
    return 12


def refresh_progress(session: Session, inventory: Inventory) -> None:
    for source in inventory.sources:
        expected = source_expected_periods(source)
        distinct_periods = {(item.period_start.year, item.period_start.month) for item in source.activity_records}
        count = len(distinct_periods)
        source.progress = min(100, round(count / max(expected, 1) * 100))
        if count == 0:
            source.status = "Pendiente"
        elif source.progress >= 100:
            source.status = "Completado"
        else:
            source.status = "En progreso"
    if inventory.sources:
        inventory.progress = round(sum(source.progress for source in inventory.sources) / len(inventory.sources))
    inventory.current_stage = "Recolección" if inventory.progress < 100 else "Cálculo"


def _seed_methodology(session: Session) -> dict[str, object]:
    units = [
        ("kWh", "kilovatio-hora", "energy"), ("MWh", "megavatio-hora", "energy"),
        ("L", "litro", "volume"), ("gal", "galón estadounidense", "volume"), ("m³", "metro cúbico", "volume"),
        ("kg", "kilogramo", "mass"), ("t", "tonelada", "mass"),
        ("km", "kilómetro", "distance"), ("t·km", "tonelada-kilómetro", "transport"),
        ("pasajero·km", "pasajero-kilómetro", "transport"), ("COP", "peso colombiano", "currency"),
    ]
    for code, name, dimension in units:
        session.add(UnitDefinition(code=code, name=name, dimension=dimension))
    session.add_all([
        UnitConversion(from_unit="MWh", to_unit="kWh", multiplier=1000, source="Sistema Internacional"),
        UnitConversion(from_unit="kWh", to_unit="MWh", multiplier=0.001, source="Sistema Internacional"),
        UnitConversion(from_unit="gal", to_unit="L", multiplier=3.785411784, source="Conversión estándar US gallon"),
        UnitConversion(from_unit="L", to_unit="gal", multiplier=1 / 3.785411784, source="Conversión estándar US gallon"),
        UnitConversion(from_unit="t", to_unit="kg", multiplier=1000, source="Sistema Internacional"),
        UnitConversion(from_unit="kg", to_unit="t", multiplier=0.001, source="Sistema Internacional"),
    ])

    gases: dict[str, Gas] = {}
    for code, name, formula in [
        ("CO2", "Dióxido de carbono", "CO₂"),
        ("CH4", "Metano", "CH₄"),
        ("N2O", "Óxido nitroso", "N₂O"),
        ("CO2e", "Dióxido de carbono equivalente directo", "CO₂e"),
        ("RF-DEMO", "Refrigerante demostrativo", "RF"),
    ]:
        gas = Gas(code=code, name=name, formula=formula)
        session.add(gas)
        session.flush()
        gases[code] = gas
    for code, value in {"CO2": 1, "CH4": 27.9, "N2O": 273, "CO2e": 1, "RF-DEMO": 2088}.items():
        session.add(GWPValue(gas_id=gases[code].id, assessment="AR6", horizon_years=100, value=value, source="Biblioteca metodológica demostrativa", status="Aprobado"))

    factor_specs = [
        ("Electricidad de red Colombia · demo", "Electricidad adquirida", "CO2e", 0.220, "kWh", "kg CO2e", "Valor demostrativo equivalente a 0,220 tCO₂e/MWh; sustituir por factor oficial del periodo.", 2024),
        ("Diésel combustión fija · CO2 demo", "Combustión fija", "CO2", 2.676, "L", "kg gas", "Componente demostrativo para validar el motor.", 2025),
        ("Diésel combustión fija · CH4 demo", "Combustión fija", "CH4", 0.00013, "L", "kg gas", "Componente demostrativo para validar el motor.", 2025),
        ("Diésel combustión fija · N2O demo", "Combustión fija", "N2O", 0.000025, "L", "kg gas", "Componente demostrativo para validar el motor.", 2025),
        ("Gasolina vehículos · CO2e demo", "Combustión móvil", "CO2e", 2.31, "L", "kg CO2e", "Factor demostrativo de combustión móvil.", 2025),
        ("Refrigerante · demo", "Emisiones fugitivas", "RF-DEMO", 1.0, "kg", "kg gas", "El dato de actividad corresponde a kg liberados; el GWP realiza la conversión.", 2025),
        ("Residuos gestionados · demo", "Residuos operacionales", "CO2e", 450.0, "t", "kg CO2e", "Factor demostrativo por tonelada gestionada.", 2025),
        ("Transporte de carga · demo", "Transporte y distribución", "CO2e", 0.12, "t·km", "kg CO2e", "Factor demostrativo por tonelada-kilómetro.", 2025),
    ]
    versions: dict[str, EmissionFactorVersion] = {}
    for name, activity, gas_code, value, input_unit, output_unit, notes, year in factor_specs:
        factor = EmissionFactor(name=name, activity_type=activity, country="Colombia", sector="Multisectorial", status="Activo", is_demo=True)
        session.add(factor)
        session.flush()
        version = EmissionFactorVersion(
            factor_id=factor.id,
            gas_id=gases[gas_code].id,
            version="1.0-demo",
            value=value,
            input_unit=input_unit,
            output_unit=output_unit,
            source_organization="Biblioteca demostrativa Calcula tu Huella",
            source_document="Datos de prueba del motor V0.4",
            publication_year=year,
            geographic_scope="Colombia · demostrativo",
            technology_scope="Genérico",
            uncertainty_percentage=10,
            status="Aprobado",
            notes=notes,
            approved_by="Comité metodológico demo",
            approved_at=datetime.now(UTC),
        )
        session.add(version)
        session.flush()
        versions[name] = version
    return {"gases": gases, "versions": versions}


def _seed_sector_templates(session: Session) -> dict[str, SectorTemplate]:
    specs = {
        "Manufactura": {
            "description": "Fuentes frecuentes de energía, procesos, refrigerantes, materiales, residuos y logística.",
            "items": [
                ("Electricidad", 2, "Energía adquirida", "Mensual", "kWh", "Alta", "Contabilidad", "bolt", "Electricidad adquirida", True),
                ("Combustibles en equipos fijos", 1, "Combustión fija", "Mensual", "L", "Alta", "Mantenimiento", "fuel", "Combustión fija", True),
                ("Vehículos propios", 1, "Combustión móvil", "Mensual", "L", "Media", "Logística", "truck", "Combustión móvil", True),
                ("Refrigerantes", 1, "Emisiones fugitivas", "Anual", "kg", "Media", "Mantenimiento", "snow", "Emisiones fugitivas", True),
                ("Materias primas", 3, "Bienes y servicios adquiridos", "Mensual", "t", "Alta", "Compras", "material", "Bienes y servicios adquiridos", True),
                ("Residuos gestionados", 3, "Residuos operacionales", "Mensual", "t", "Media", "Gestión ambiental", "waste", "Residuos operacionales", True),
                ("Transporte contratado", 3, "Transporte y distribución", "Mensual", "t·km", "Alta", "Logística", "route", "Transporte y distribución", True),
            ],
        },
        "Transporte y logística": {
            "description": "Modelo para flota propia, transporte contratado, almacenamiento y cadena de frío.",
            "items": [
                ("Flota propia", 1, "Combustión móvil", "Mensual", "L", "Alta", "Jefatura de flota", "truck", "Combustión móvil", True),
                ("Electricidad de sedes", 2, "Energía adquirida", "Mensual", "kWh", "Media", "Administración", "bolt", "Electricidad adquirida", True),
                ("Refrigerantes de cadena de frío", 1, "Emisiones fugitivas", "Anual", "kg", "Media", "Mantenimiento", "snow", "Emisiones fugitivas", False),
                ("Transporte subcontratado", 3, "Transporte y distribución", "Mensual", "t·km", "Alta", "Operaciones", "route", "Transporte y distribución", True),
                ("Viajes de negocios", 3, "Viajes de negocios", "Trimestral", "pasajero·km", "Baja", "Talento humano", "plane", "Viajes de negocios", False),
            ],
        },
        "Servicios y oficinas": {
            "description": "Modelo simplificado para oficinas, servicios profesionales y operaciones administrativas.",
            "items": [
                ("Electricidad", 2, "Energía adquirida", "Mensual", "kWh", "Alta", "Administración", "bolt", "Electricidad adquirida", True),
                ("Plantas de emergencia", 1, "Combustión fija", "Mensual", "L", "Media", "Mantenimiento", "fuel", "Combustión fija", False),
                ("Refrigerantes", 1, "Emisiones fugitivas", "Anual", "kg", "Media", "Mantenimiento", "snow", "Emisiones fugitivas", True),
                ("Viajes de negocios", 3, "Viajes de negocios", "Trimestral", "pasajero·km", "Media", "Talento humano", "plane", "Viajes de negocios", True),
                ("Desplazamiento de empleados", 3, "Movilidad de empleados", "Anual", "pasajero·km", "Media", "Talento humano", "people", "Movilidad de empleados", True),
                ("Residuos de oficina", 3, "Residuos operacionales", "Mensual", "kg", "Baja", "Servicios generales", "waste", "Residuos operacionales", False),
            ],
        },
        "Agroindustria": {
            "description": "Fuentes agrícolas, pecuarias, energéticas y de transformación primaria.",
            "items": [
                ("Electricidad", 2, "Energía adquirida", "Mensual", "kWh", "Media", "Administración", "bolt", "Electricidad adquirida", True),
                ("Combustibles de maquinaria", 1, "Combustión móvil", "Mensual", "L", "Alta", "Operaciones", "tractor", "Combustión móvil", True),
                ("Fertilizantes nitrogenados", 1, "Suelos gestionados", "Mensual", "kg", "Alta", "Agronomía", "leaf", "Suelos gestionados", True),
                ("Fermentación entérica", 1, "Ganadería", "Mensual", "kg", "Alta", "Producción pecuaria", "animal", "Ganadería", False),
                ("Manejo de estiércol", 1, "Manejo de estiércol", "Mensual", "t", "Alta", "Producción pecuaria", "waste", "Manejo de estiércol", False),
                ("Residuos orgánicos", 3, "Residuos operacionales", "Mensual", "t", "Media", "Gestión ambiental", "waste", "Residuos operacionales", True),
                ("Transporte de insumos y producto", 3, "Transporte y distribución", "Mensual", "t·km", "Media", "Logística", "route", "Transporte y distribución", True),
            ],
        },
        "Gestión de residuos": {
            "description": "Modelo para recepción, transporte, compostaje, digestión, disposición y aprovechamiento.",
            "items": [
                ("Electricidad", 2, "Energía adquirida", "Mensual", "kWh", "Media", "Administración", "bolt", "Electricidad adquirida", True),
                ("Combustibles de operación", 1, "Combustión móvil", "Mensual", "L", "Alta", "Operaciones", "fuel", "Combustión móvil", True),
                ("Compostaje", 1, "Tratamiento propio de residuos", "Mensual", "t", "Alta", "Operaciones", "compost", "Tratamiento propio de residuos", True),
                ("Digestión anaerobia", 1, "Tratamiento propio de residuos", "Mensual", "t", "Alta", "Operaciones", "biogas", "Tratamiento propio de residuos", False),
                ("Fugas de biogás", 1, "Emisiones fugitivas", "Mensual", "kg", "Alta", "Mantenimiento", "gas", "Emisiones fugitivas", False),
                ("Transporte contratado", 3, "Transporte y distribución", "Mensual", "t·km", "Media", "Logística", "route", "Transporte y distribución", True),
                ("Residuos enviados a terceros", 3, "Residuos operacionales", "Mensual", "t", "Media", "Gestión ambiental", "waste", "Residuos operacionales", True),
            ],
        },
    }
    templates: dict[str, SectorTemplate] = {}
    for sector, config in specs.items():
        template = SectorTemplate(name=f"Modelo sectorial · {sector}", sector=sector, description=config["description"], version="1.0", active=True)
        session.add(template)
        session.flush()
        templates[sector] = template
        for name, scope, category, frequency, unit, materiality, responsible, icon, activity_type, recommended in config["items"]:
            session.add(SectorTemplateSource(
                template_id=template.id, name=name, scope=scope, category=category,
                description=f"Fuente sugerida para el modelo de {sector}.", data_frequency=frequency,
                preferred_unit=unit, materiality=materiality, responsible=responsible, icon=icon,
                factor_activity_type=activity_type, recommended=recommended,
            ))
    return templates


def _ensure_v012_defaults(session: Session) -> None:
    """Completa membresías y configuración V0.12 sin alterar inventarios existentes."""
    for user in session.scalars(select(AppUser)):
        membership = session.scalar(select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == user.organization_id,
        ))
        if not membership:
            session.add(OrganizationMembership(
                user_id=user.id, organization_id=user.organization_id, role=user.role, active=user.active
            ))
    session.flush()
    if not settings.seed_demo:
        return

    if settings.seed_demo:
        primary = session.scalar(select(Organization).order_by(Organization.id).limit(1))
        second = session.scalar(select(Organization).where(Organization.name == "Transportes Horizonte Demo S.A.S."))
        if primary and not second:
            second = Organization(
                name="Transportes Horizonte Demo S.A.S.", trade_name="Transportes Horizonte",
                tax_id="901.888.420-1", sector="Transporte y logística", ciiu_code="H4923",
                country="Colombia", department="Antioquia", city="Medellín", employees=64,
                annual_revenue=8_900_000_000, contact_name="Sofía Restrepo",
                contact_email="ambiental@transporteshorizonte.demo", status="Activa",
            )
            session.add(second)
            session.flush()
            facility = Facility(
                organization_id=second.id, name="Centro logístico Bello", facility_type="Centro logístico",
                city="Bello", address="Autopista Norte", employees=64, operational_control=True,
            )
            session.add(facility)
            session.flush()
            inventory = Inventory(
                organization_id=second.id, name="Inventario corporativo 2025",
                start_date=date(2025, 1, 1), end_date=date(2025, 12, 31), base_year=2025,
                objective="Inventario piloto multiempresa", methodology="GHG Protocol + ISO 14064-1",
                methodology_version="GHG Protocol Corporate Standard · ISO 14064-1:2018",
                gwp_version="IPCC AR6 · 100 años", status="Borrador", progress=15,
                current_stage="Configuración", version="0.20",
                notes="Organización demostrativa para validar la operación multiempresa y operación SaaS, flujo comercial y operación contractual y éxito del cliente, inteligencia de impacto y riesgos climáticos V0.20.",
            )
            session.add(inventory)
            session.flush()
            session.add(InventoryFacility(inventory_id=inventory.id, facility_id=facility.id, included=True, inclusion_percentage=100))
            session.add_all([
                EmissionSource(inventory_id=inventory.id, facility_id=facility.id, name="Flota propia", scope=1, category="Combustión móvil", responsible="Jefatura de flota", materiality="Alta", data_frequency="Mensual", preferred_unit="L", icon="truck"),
                EmissionSource(inventory_id=inventory.id, facility_id=facility.id, name="Electricidad de sedes", scope=2, category="Energía adquirida", responsible="Administración", materiality="Media", data_frequency="Mensual", preferred_unit="kWh", icon="bolt"),
                EmissionSource(inventory_id=inventory.id, facility_id=facility.id, name="Transporte subcontratado", scope=3, category="Transporte y distribución", responsible="Operaciones", materiality="Alta", data_frequency="Mensual", preferred_unit="t·km", icon="route"),
            ])
            session.flush()
            for user in session.scalars(select(AppUser).where(AppUser.role.in_(["Administrador", "Consultor"]))):
                session.add(OrganizationMembership(user_id=user.id, organization_id=second.id, role=user.role, active=True))

    session.flush()
    organizations = list(session.scalars(select(Organization)))
    from .automations import calculate_next_run, hash_api_key
    for org in organizations:
        if not session.scalar(select(ScheduledAutomation).where(ScheduledAutomation.organization_id == org.id).limit(1)):
            latest_inventory = session.scalar(select(Inventory).where(Inventory.organization_id == org.id).order_by(Inventory.start_date.desc()).limit(1))
            defaults = [
                ScheduledAutomation(organization_id=org.id, inventory_id=latest_inventory.id if latest_inventory else None, name="Recordar información pendiente", automation_type="Recordatorio de solicitudes", cadence="Diaria", schedule_time="08:00", timezone="America/Bogota", recipient_roles='["Consultor", "Cliente"]', days_before=3, active=True, created_by="sistema"),
                ScheduledAutomation(organization_id=org.id, inventory_id=latest_inventory.id if latest_inventory else None, name="Revisar hallazgos abiertos", automation_type="Seguimiento de observaciones", cadence="Semanal", schedule_time="09:00", weekday=0, timezone="America/Bogota", recipient_roles='["Consultor", "Revisor"]', days_before=5, active=True, created_by="sistema"),
                ScheduledAutomation(organization_id=org.id, inventory_id=latest_inventory.id if latest_inventory else None, name="Resumen ejecutivo semanal", automation_type="Resumen ejecutivo", cadence="Semanal", schedule_time="07:30", weekday=4, timezone="America/Bogota", recipient_roles='["Administrador", "Consultor"]', days_before=0, active=True, created_by="sistema"),
            ]
            for automation in defaults:
                session.add(automation)
                session.flush()
                automation.next_run_at = calculate_next_run(automation)
        if not session.scalar(select(IntegrationConnection).where(IntegrationConnection.organization_id == org.id).limit(1)):
            demo_key = f"cth_demo_{org.id}_2026"
            session.add(IntegrationConnection(
                organization_id=org.id, name="API de datos corporativos", provider="API REST",
                integration_type="Entrada de datos", status="Verificada",
                api_key_hash=hash_api_key(demo_key), api_key_prefix=demo_key[:10],
                config_json='{"scope": "activity_data", "demo": true}',
                last_test_at=datetime.now(UTC), last_test_detail="Integración demostrativa disponible",
                active=True, created_by="sistema",
            ))


def _ensure_v013_defaults(session: Session) -> None:
    """Inicializa gobierno metodológico, cumplimiento, documentos y alistamiento comercial V0.13."""
    _ensure_v012_defaults(session)
    requirement_specs = [
        ("GHG Protocol", "GHG-LIM-01", "Límites organizacionales definidos", "El inventario documenta el enfoque de consolidación y las operaciones incluidas.", "Acta metodológica y matriz de sedes", 10),
        ("GHG Protocol", "GHG-SCP-01", "Fuentes clasificadas por alcance", "Cada fuente se clasifica de forma coherente en alcance 1, 2 o 3.", "Matriz de fuentes y justificaciones", 20),
        ("GHG Protocol", "GHG-BAS-01", "Año base y recalculo documentados", "Existe una política para seleccionar y recalcular el año base.", "Política de año base", 30),
        ("ISO 14064-1", "ISO-DAT-01", "Datos de actividad trazables", "Los datos conservan periodo, unidad, origen, responsable y evidencia.", "Registros de actividad y soportes", 40),
        ("ISO 14064-1", "ISO-FAC-01", "Factores de emisión controlados", "Los factores tienen fuente, versión, vigencia, unidad y aprobación.", "Biblioteca de factores", 50),
        ("ISO 14064-1", "ISO-QA-01", "Controles de calidad aplicados", "Se ejecutan validaciones automáticas y revisión profesional.", "Alertas, observaciones y decisiones", 60),
        ("ISO 14064-1", "ISO-REP-01", "Informe completo y consistente", "El informe revela metodología, límites, fuentes, resultados, exclusiones y calidad.", "Informe técnico aprobado", 70),
        ("Verificación", "VER-AUD-01", "Pista de auditoría disponible", "Cada resultado puede rastrearse hasta dato, factor, fórmula, evidencia y aprobación.", "Auditoría y paquete de verificación", 80),
        ("Gestión documental", "DOC-CTL-01", "Documentos versionados y retenidos", "Los soportes e informes tienen código, versión, propietario, confidencialidad y retención.", "Registro maestro documental", 90),
        ("Seguridad", "SEC-ACC-01", "Accesos segregados por organización", "Los usuarios solo acceden a organizaciones y funciones autorizadas.", "Membresías, roles y auditoría", 100),
    ]
    for framework, code, title, description, evidence_expected, order in requirement_specs:
        if not session.scalar(select(ComplianceRequirement).where(ComplianceRequirement.code == code)):
            session.add(ComplianceRequirement(
                framework=framework, code=code, title=title, description=description,
                evidence_expected=evidence_expected, mandatory=True, display_order=order,
            ))
    session.flush()

    readiness_specs = [
        ("Producto", "MVP funcional validado con inventarios piloto", "En progreso", "Dirección de producto", 10),
        ("Producto", "Factores oficiales del periodo cargados y aprobados", "Pendiente", "Dirección metodológica", 20),
        ("Legal", "Disponibilidad jurídica de la marca validada", "Pendiente", "Asesoría jurídica", 30),
        ("Legal", "Términos, privacidad y tratamiento de datos aprobados", "Pendiente", "Asesoría jurídica", 40),
        ("Comercial", "Planes, precios y propuesta económica aprobados", "En progreso", "Dirección comercial", 50),
        ("Comercial", "Caso de éxito e informe demostrativo publicados", "Pendiente", "Mercadeo", 60),
        ("Operación", "Soporte, respaldo y recuperación ensayados", "En progreso", "Administración de plataforma", 70),
        ("Seguridad", "Despliegue productivo con HTTPS y PostgreSQL", "Pendiente", "Tecnología", 80),
        ("Metodología", "Manual metodológico y control de cambios aprobados", "En progreso", "Dirección metodológica", 90),
        ("Metodología", "Separación entre revisión interna y verificación externa documentada", "Completado", "Dirección metodológica", 100),
    ]

    requirements = list(session.scalars(select(ComplianceRequirement).order_by(ComplianceRequirement.display_order)))
    organizations = list(session.scalars(select(Organization)))
    for org in organizations:
        if not session.scalar(select(MethodologyRelease).where(MethodologyRelease.organization_id == org.id).limit(1)):
            session.add_all([
                MethodologyRelease(organization_id=org.id, name="Marco corporativo de inventarios", version="1.0", issuing_body="Calcula tu Huella", publication_date=date(2026, 7, 31), effective_from=date(2026, 7, 31), status="Aprobado", source_reference="Manual metodológico interno", content_hash=hashlib.sha256(b"Calcula tu Huella metodologia 1.0").hexdigest(), notes="Configuración inicial basada en GHG Protocol e ISO 14064-1.", approved_by="Comité metodológico", approved_at=datetime.now(UTC)),
                MethodologyRelease(organization_id=org.id, name="Matriz sectorial", version="1.0", issuing_body="Calcula tu Huella", publication_date=date(2026, 7, 31), effective_from=date(2026, 7, 31), status="Aprobado", source_reference="Configuración sectorial V0.13", content_hash=hashlib.sha256(f"{org.sector}-sectorial-1.0".encode()).hexdigest(), notes=f"Modelo sectorial para {org.sector}.", approved_by="Comité metodológico", approved_at=datetime.now(UTC)),
            ])
        for category, title, status, owner, order in readiness_specs:
            if not session.scalar(select(CommercialReadinessItem).where(CommercialReadinessItem.organization_id == org.id, CommercialReadinessItem.category == category, CommercialReadinessItem.title == title)):
                session.add(CommercialReadinessItem(organization_id=org.id, category=category, title=title, status=status, owner=owner, display_order=order, updated_by="sistema"))
        session.flush()
        inventories = list(session.scalars(select(Inventory).where(Inventory.organization_id == org.id)))
        for inventory in inventories:
            if not session.scalar(select(InventoryMethodologySnapshot).where(InventoryMethodologySnapshot.inventory_id == inventory.id).limit(1)):
                release = session.scalar(select(MethodologyRelease).where(MethodologyRelease.organization_id == org.id, MethodologyRelease.status == "Aprobado").order_by(MethodologyRelease.id).limit(1))
                session.add(InventoryMethodologySnapshot(
                    inventory_id=inventory.id, methodology_release_id=release.id if release else None,
                    snapshot_name=f"Configuración metodológica · {inventory.name}", status="Aprobado",
                    methodology_name=inventory.methodology, methodology_version=inventory.methodology_version,
                    gwp_version=inventory.gwp_version, consolidation_approach=inventory.consolidation_approach,
                    materiality_threshold=inventory.materiality_threshold,
                    policy_json='{"base_year": "recalculo controlado", "biogenic_co2": "separado", "offsets": "fuera del inventario bruto"}',
                    approved_by="Comité metodológico", approved_at=datetime.now(UTC),
                ))
            for requirement in requirements:
                if not session.scalar(select(ComplianceAssessment).where(ComplianceAssessment.inventory_id == inventory.id, ComplianceAssessment.requirement_id == requirement.id)):
                    initial_status = "Cumple" if requirement.code in {"SEC-ACC-01", "VER-AUD-01"} else "Parcial"
                    session.add(ComplianceAssessment(
                        inventory_id=inventory.id, requirement_id=requirement.id, status=initial_status,
                        owner="Responsable ambiental", notes="Evaluación inicial automática V0.13", updated_by="sistema",
                    ))
        session.flush()
        if not session.scalar(select(DocumentControlRecord).where(DocumentControlRecord.organization_id == org.id).limit(1)):
            latest_inventory = session.scalar(select(Inventory).where(Inventory.organization_id == org.id).order_by(Inventory.start_date.desc()).limit(1))
            session.add_all([
                DocumentControlRecord(organization_id=org.id, inventory_id=latest_inventory.id if latest_inventory else None, document_code="MET-MAN-001", title="Manual metodológico corporativo", category="Metodología", version="1.0", owner="Dirección metodológica", confidentiality="Interno", retention_years=10, status="Vigente", sha256=hashlib.sha256(b"manual-metodologico-1.0").hexdigest(), notes="Registro maestro demostrativo.", created_by="sistema"),
                DocumentControlRecord(organization_id=org.id, inventory_id=latest_inventory.id if latest_inventory else None, document_code="REP-TEC-001", title="Informe técnico de huella de carbono", category="Informe", version="Borrador", owner="Consultoría", confidentiality="Confidencial", retention_years=7, status="En elaboración", notes="Se vinculará con el informe aprobado.", created_by="sistema"),
            ])


def _ensure_v014_defaults(session: Session) -> None:
    """Inicializa planes, suscripciones, onboarding, facturación y soporte V0.14."""
    _ensure_v013_defaults(session)
    plan_specs = [
        ("ESENCIAL", "Huella Esencial", "Una sede, alcances 1 y 2, informe ejecutivo y acompañamiento básico.", 390000, 3900000, 5, 2, 3, 1024, False, False),
        ("EMPRESARIAL", "Huella Empresarial", "Hasta cinco sedes, alcance 3 priorizado, informes técnicos y gestión anual.", 990000, 9900000, 20, 5, 8, 5120, True, True),
        ("CORPORATIVO", "Gestión Corporativa", "Operación multiempresa, alcance 3 avanzado, verificación, integraciones y soporte prioritario.", 2490000, 24900000, 100, 50, 30, 51200, True, True),
    ]
    for code, name, description, monthly, annual, users, facilities, inventories, storage_mb, scope3, verification in plan_specs:
        plan = session.scalar(select(ServicePlan).where(ServicePlan.code == code))
        if not plan:
            session.add(ServicePlan(
                code=code, name=name, description=description, monthly_fee=monthly, annual_fee=annual,
                max_users=users, max_facilities=facilities, max_inventories=inventories, max_storage_mb=storage_mb,
                includes_scope3=scope3, includes_verification_portal=verification, active=True,
            ))
    session.flush()
    default_plan = session.scalar(select(ServicePlan).where(ServicePlan.code == "EMPRESARIAL"))
    onboarding_specs = [
        ("ORG-01", "Organización", "Completar información legal y operativa", "Registrar razón social, NIT, sector, contacto y sedes.", "Cliente", 10),
        ("USR-01", "Accesos", "Invitar responsables y definir roles", "Asignar responsables de carga, revisión y aprobación.", "Administrador", 20),
        ("MET-01", "Metodología", "Aprobar metodología y límites", "Definir estándar, GWP, año base, enfoque de consolidación y materialidad.", "Consultor", 30),
        ("DAT-01", "Información", "Cargar el primer conjunto de datos", "Registrar consumos, evidencias y responsables para una fuente piloto.", "Cliente", 40),
        ("CAL-01", "Cálculo", "Validar el primer cálculo trazable", "Confirmar unidad, factor, fórmula y resultado por gas.", "Consultor", 50),
        ("REP-01", "Entrega", "Generar el primer informe", "Emitir y revisar un informe ejecutivo de demostración.", "Consultor", 60),
    ]
    organizations = list(session.scalars(select(Organization)))
    for org in organizations:
        subscription = session.scalar(select(OrganizationSubscription).where(OrganizationSubscription.organization_id == org.id))
        if not subscription and default_plan:
            subscription = OrganizationSubscription(
                organization_id=org.id, plan_id=default_plan.id, billing_cycle="Anual", status="Prueba",
                start_date=date(2026, 7, 31), trial_end=date(2026, 8, 30), renewal_date=date(2027, 7, 31),
                notes="Suscripción demostrativa V0.14. No representa un cobro real.",
            )
            session.add(subscription)
            session.flush()
        for code, category, title, description, owner, order in onboarding_specs:
            if not session.scalar(select(CustomerOnboardingItem).where(CustomerOnboardingItem.organization_id == org.id, CustomerOnboardingItem.code == code)):
                initial = "Completado" if code in {"ORG-01", "USR-01"} else "En progreso" if code == "MET-01" else "Pendiente"
                session.add(CustomerOnboardingItem(
                    organization_id=org.id, code=code, category=category, title=title, description=description,
                    status=initial, owner=owner, display_order=order, updated_by="sistema",
                    completed_at=datetime.now(UTC) if initial == "Completado" else None,
                ))
        if subscription and not session.scalar(select(BillingInvoice).where(BillingInvoice.organization_id == org.id).limit(1)):
            amount = subscription.custom_monthly_fee or (default_plan.annual_fee if default_plan else 0)
            session.add(BillingInvoice(
                organization_id=org.id, subscription_id=subscription.id, reference=f"DEMO-{org.id}-2026",
                period_start=date(2026, 7, 31), period_end=date(2027, 7, 30), amount=amount, status="Demostrativa",
                issued_at=date(2026, 7, 31), due_date=date(2026, 8, 15), notes="Documento demostrativo. No constituye factura electrónica.",
            ))
        if not session.scalar(select(SupportTicket).where(SupportTicket.organization_id == org.id).limit(1)):
            session.add(SupportTicket(
                organization_id=org.id, created_by=org.contact_email or "cliente@calculatuhuella.local",
                category="Acompañamiento inicial", priority="Normal", status="En gestión",
                subject="Validar configuración del primer inventario",
                description="Revisar que las sedes, responsables y límites organizacionales estén completos.",
                assigned_to="Equipo de implementación",
            ))
    session.flush()


def _ensure_v015_defaults(session: Session) -> None:
    """Inicializa diagnóstico comercial, propuestas, aceptación y pagos V0.15."""
    _ensure_v014_defaults(session)
    if not settings.seed_demo:
        return
    lead = session.scalar(select(CommercialLead).where(CommercialLead.email == "gerencia@cafedemo.co"))
    if not lead:
        lead = CommercialLead(
            public_token=secrets.token_urlsafe(24), company_name="Café Montaña Demo S.A.S.",
            contact_name="Valentina Gómez", email="gerencia@cafedemo.co", phone="300 555 0101",
            sector="Agroindustria", city="Manizales", employees_band="51 a 200", facilities_count=3,
            has_previous_inventory=False, desired_scopes="Alcances 1, 2 y 3 priorizado",
            objective="Requisito de clientes y estrategia de reducción", urgency="Alta",
            notes="Prospecto demostrativo generado desde el diagnóstico público.", complexity_score=12,
            recommended_plan_code="EMPRESARIAL", status="Calificado", assigned_to="Carlos Uribe",
        )
        session.add(lead)
        session.flush()
    plan = session.scalar(select(ServicePlan).where(ServicePlan.code == "EMPRESARIAL"))
    proposal = session.scalar(select(CommercialProposal).where(CommercialProposal.reference == "PROP-DEMO-2026-001"))
    if not proposal:
        recurring = plan.annual_fee if plan else 9_900_000
        implementation = 8_500_000
        proposal = CommercialProposal(
            lead_id=lead.id, plan_id=plan.id if plan else None, reference="PROP-DEMO-2026-001",
            public_token=secrets.token_urlsafe(24), title="Implementación de inventario corporativo de GEI",
            company_name=lead.company_name, contact_name=lead.contact_name, contact_email=lead.email,
            status="Enviada", valid_until=date(2026, 8, 31), billing_cycle="Anual",
            implementation_fee=implementation, recurring_fee=recurring, discount_amount=0, tax_rate=19,
            first_year_total=round((implementation + recurring) * 1.19, 2),
            scope_json='["Caracterización y límites", "Alcances 1 y 2", "Alcance 3 priorizado", "Dashboard e informe técnico"]',
            deliverables_json='["Inventario corporativo", "Informe ejecutivo y técnico", "Memoria de cálculo", "Plan inicial de reducción"]',
            terms="Implementación estimada de 8 a 10 semanas. La verificación independiente no está incluida.",
            contract_version="1.0", created_by="consultor@calculatuhuella.local", sent_at=datetime.now(UTC),
        )
        session.add(proposal)
        session.flush()
    if not session.scalar(select(PaymentTransaction).where(PaymentTransaction.proposal_id == proposal.id)):
        session.add(PaymentTransaction(
            proposal_id=proposal.id, public_token=secrets.token_urlsafe(24), gateway="Demo",
            status="Pendiente", amount=proposal.first_year_total, currency="COP",
            external_reference=f"PAY-{proposal.reference}", payer_name=proposal.contact_name, payer_email=proposal.contact_email,
            provider_payload='{"mode": "demo", "notice": "No procesa dinero real"}',
        ))
    session.flush()



def _ensure_v016_defaults(session: Session) -> None:
    """Inicializa contratos, órdenes, cartera y documentos de cobro V0.16."""
    _ensure_v015_defaults(session)
    if not settings.seed_demo:
        return

    org = session.scalar(select(Organization).order_by(Organization.id).limit(1))
    if not org:
        return
    subscription = session.scalar(select(OrganizationSubscription).where(OrganizationSubscription.organization_id == org.id))
    invoice = session.scalar(select(BillingInvoice).where(BillingInvoice.organization_id == org.id).order_by(BillingInvoice.id))
    proposal = session.scalar(select(CommercialProposal).where(CommercialProposal.organization_id == org.id).order_by(CommercialProposal.id))

    contract = session.scalar(select(ServiceContract).where(ServiceContract.reference == "CTR-DEMO-2026-001"))
    if not contract:
        contract = ServiceContract(
            organization_id=org.id, proposal_id=proposal.id if proposal else None,
            reference="CTR-DEMO-2026-001", title="Servicio anual de gestión de huella de carbono",
            version="1.0", status="Vigente", start_date=date(2026, 7, 31), end_date=date(2027, 7, 30),
            renewal_type="Anual", auto_renew=True, notice_days=45,
            contract_value=(subscription.plan.annual_fee if subscription and subscription.plan else 9_900_000),
            billing_cycle="Anual", owner="Dirección de servicio",
            terms_snapshot="Prestación del servicio SaaS, acompañamiento metodológico y generación de entregables conforme al plan contratado.",
            signed_by="Representante legal demo", signed_email=org.contact_email,
            signed_at=datetime(2026, 7, 31, 15, 0, tzinfo=UTC), created_by="sistema",
        )
        payload = f"{contract.reference}|{contract.organization_id}|{contract.start_date}|{contract.end_date}|{contract.contract_value}|{contract.terms_snapshot}|{contract.signed_by}|{contract.signed_email}"
        contract.signature_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        session.add(contract)
        session.flush()

    if not session.scalar(select(ServiceOrder).where(ServiceOrder.reference == "OS-DEMO-2026-001")):
        session.add(ServiceOrder(
            organization_id=org.id, contract_id=contract.id, reference="OS-DEMO-2026-001",
            title="Implementación del inventario corporativo 2025", service_type="Implementación",
            description="Configuración inicial, levantamiento de información, cálculo, revisión y primer informe.",
            status="En ejecución", planned_start=date(2026, 8, 1), planned_end=date(2026, 10, 15),
            owner="Equipo de implementación", acceptance_criteria="Inventario calculado, revisado y con informe técnico disponible.",
            notes="Orden demostrativa creada para validar la operación posterior a la venta.", created_by="sistema",
        ))

    if invoice and not session.scalar(select(CollectionAction).where(CollectionAction.invoice_id == invoice.id).limit(1)):
        session.add(CollectionAction(
            organization_id=org.id, invoice_id=invoice.id, action_type="Confirmación de recepción",
            channel="Correo", recipient=org.contact_email, due_at=invoice.due_date,
            status="Pendiente", notes="Confirmar recepción del documento administrativo y fecha estimada de pago.",
            created_by="sistema",
        ))

    if invoice and not session.scalar(select(BillingDocumentRecord).where(BillingDocumentRecord.invoice_id == invoice.id).limit(1)):
        session.add(BillingDocumentRecord(
            organization_id=org.id, invoice_id=invoice.id,
            document_type="Documento de cobro interno", internal_reference=f"DOC-{invoice.reference}",
            provider="Sin integración", status="Pendiente de integración", issued_at=invoice.issued_at,
            notes="Registro interno. No constituye factura electrónica ni documento tributario emitido ante la DIAN.",
            created_by="sistema",
        ))
    session.flush()



def _ensure_v017_defaults(session: Session) -> None:
    """Inicializa perfiles de éxito, valor entregado, salud y renovaciones V0.18."""
    _ensure_v016_defaults(session)
    organizations = list(session.scalars(select(Organization).order_by(Organization.id)))
    if not organizations:
        return

    for index, org in enumerate(organizations):
        if settings.seed_demo and index == 0:
            for demo_user in session.scalars(select(AppUser).where(AppUser.organization_id == org.id)):
                if demo_user.last_login is None and demo_user.role in {"Consultor", "Cliente"}:
                    demo_user.last_login = datetime(2026, 7, 30, 14, 0, tzinfo=UTC)
        profile = session.scalar(select(CustomerSuccessProfile).where(CustomerSuccessProfile.organization_id == org.id))
        if not profile:
            profile = CustomerSuccessProfile(
                organization_id=org.id,
                lifecycle_stage="Adopción" if index == 0 else "Implementación",
                owner="Equipo de éxito del cliente",
                executive_sponsor=org.contact_name,
                sponsor_email=org.contact_email,
                primary_objective="Contar con un inventario corporativo trazable y convertir los resultados en decisiones de reducción.",
                success_plan="Completar adopción, cerrar el primer ciclo verificable, presentar valor ejecutivo y preparar la renovación con evidencia.",
                last_business_review=date(2026, 7, 15) if index == 0 else None,
                next_business_review=date(2026, 10, 15) if index == 0 else date(2026, 9, 30),
                satisfaction_score=4.2 if index == 0 else None,
                nps_score=8 if index == 0 else None,
            )
            session.add(profile)
            session.flush()

        if index == 0 and not session.scalar(select(ValueMilestone).where(ValueMilestone.organization_id == org.id).limit(1)):
            inventory = session.scalar(select(Inventory).where(Inventory.organization_id == org.id).order_by(Inventory.id))
            session.add_all([
                ValueMilestone(
                    organization_id=org.id, inventory_id=inventory.id if inventory else None,
                    title="Inventario corporativo configurado", category="Implementación", owner="Consultoría",
                    status="Completado", target_date=date(2026, 7, 31), completed_at=datetime(2026, 7, 31, 16, 0, tzinfo=UTC),
                    expected_value=1, realized_value=1, unit="inventario",
                    evidence_note="Configuración metodológica, sedes, fuentes y responsables disponibles.", created_by="sistema",
                ),
                ValueMilestone(
                    organization_id=org.id, inventory_id=inventory.id if inventory else None,
                    title="Primer informe técnico aprobado", category="Entregable", owner="Revisión técnica",
                    status="En progreso", target_date=date(2026, 10, 15), expected_value=1, realized_value=0,
                    unit="informe", evidence_note="Depende del cierre de observaciones y cobertura anual.", created_by="sistema",
                ),
                ValueMilestone(
                    organization_id=org.id, inventory_id=inventory.id if inventory else None,
                    title="Portafolio de reducción priorizado", category="Valor climático", owner="Dirección ambiental",
                    status="Planeado", target_date=date(2026, 11, 30), expected_value=3, realized_value=0,
                    unit="medidas priorizadas", evidence_note="Resultado esperado para el comité ejecutivo.", created_by="sistema",
                ),
            ])

        if index == 0 and not session.scalar(select(SuccessCommitment).where(SuccessCommitment.organization_id == org.id).limit(1)):
            session.add_all([
                SuccessCommitment(
                    organization_id=org.id, title="Validar responsables y calendario de datos",
                    description="Confirmar propietarios de información y fechas de entrega para todas las fuentes materiales.",
                    owner="Gestión ambiental", due_date=date(2026, 8, 15), priority="Alta", status="Completado",
                    source="Onboarding", completed_at=datetime(2026, 7, 29, 15, 0, tzinfo=UTC), created_by="sistema",
                ),
                SuccessCommitment(
                    organization_id=org.id, title="Resolver observaciones mayores del inventario",
                    description="Cerrar faltantes de transporte contratado y soportes de refrigerantes.",
                    owner="Equipo del cliente", due_date=date(2026, 9, 15), priority="Alta", status="En progreso",
                    source="Revisión técnica", created_by="sistema",
                ),
                SuccessCommitment(
                    organization_id=org.id, title="Preparar revisión ejecutiva trimestral",
                    description="Presentar adopción, riesgos, valor entregado y próximos resultados a dirección.",
                    owner="Éxito del cliente", due_date=date(2026, 10, 15), priority="Media", status="Pendiente",
                    source="Plan de éxito", created_by="sistema",
                ),
            ])
        session.flush()

        if not session.scalar(select(AccountHealthSnapshot).where(AccountHealthSnapshot.organization_id == org.id).limit(1)):
            from .customer_success import refresh_account_health, sync_renewal_opportunity
            snapshot = refresh_account_health(session, org.id, "sistema")
            sync_renewal_opportunity(session, org.id, snapshot, "sistema")
        else:
            latest = session.scalar(
                select(AccountHealthSnapshot)
                .where(AccountHealthSnapshot.organization_id == org.id)
                .order_by(AccountHealthSnapshot.calculated_at.desc())
            )
            if latest:
                from .customer_success import sync_renewal_opportunity
                sync_renewal_opportunity(session, org.id, latest, "sistema")
    session.flush()


def _ensure_v018_defaults(session: Session) -> None:
    """Inicializa referencias y snapshots de analítica de impacto V0.18."""
    _ensure_v017_defaults(session)
    if not settings.seed_demo:
        return
    from .impact_intelligence import refresh_impact_snapshot
    for org in session.scalars(select(Organization)):
        inventory = session.scalar(
            select(Inventory).where(Inventory.organization_id == org.id).order_by(Inventory.start_date.desc(), Inventory.id.desc())
        )
        if not inventory:
            continue
        inventory.version = "0.18" if inventory.version == "0.17" else inventory.version
        current_refs = session.scalar(select(BenchmarkReference).where(BenchmarkReference.organization_id == org.id).limit(1))
        if not current_refs:
            employees = max(org.employees, 1)
            total = sum(source.emissions for source in inventory.sources if source.included)
            intensity_employee = total / employees if total else 8.0
            intensity_revenue = total / max(org.annual_revenue / 1_000_000_000, 1) if total else 90.0
            session.add_all([
                BenchmarkReference(
                    organization_id=org.id, name="Intensidad por empleado · referencia interna", sector=org.sector,
                    metric_code="intensity_employee", metric_name="Intensidad por empleado", period_label="2025", unit="tCO₂e/empleado",
                    median_value=round(max(intensity_employee * 1.15, 0.01), 4), top_quartile_value=round(max(intensity_employee * 0.80, 0.01), 4),
                    lower_is_better=True, source_type="Referencia interna demostrativa",
                    source_reference="Construida para validar el módulo; reemplazar por fuente sectorial documentada.", confidence_level="Baja",
                    notes="No constituye un benchmark oficial.", created_by="sistema",
                ),
                BenchmarkReference(
                    organization_id=org.id, name="Intensidad por ingresos · referencia interna", sector=org.sector,
                    metric_code="intensity_revenue_billion", metric_name="Intensidad por ingresos", period_label="2025", unit="tCO₂e/mil millones COP",
                    median_value=round(max(intensity_revenue * 1.20, 0.01), 4), top_quartile_value=round(max(intensity_revenue * 0.75, 0.01), 4),
                    lower_is_better=True, source_type="Referencia interna demostrativa",
                    source_reference="Construida para validar el módulo; reemplazar por fuente sectorial documentada.", confidence_level="Baja",
                    notes="No constituye un benchmark oficial.", created_by="sistema",
                ),
                BenchmarkReference(
                    organization_id=org.id, name="Calidad documental · meta operativa", sector=org.sector,
                    metric_code="quality_score", metric_name="Calidad de datos", period_label="Meta interna", unit="%",
                    median_value=75, top_quartile_value=90, lower_is_better=False, source_type="Meta corporativa",
                    source_reference="Umbral interno de gestión de calidad de datos.", confidence_level="Alta", created_by="sistema",
                ),
                BenchmarkReference(
                    organization_id=org.id, name="Cobertura de evidencias · meta operativa", sector=org.sector,
                    metric_code="evidence_coverage", metric_name="Cobertura de evidencias", period_label="Meta interna", unit="%",
                    median_value=80, top_quartile_value=95, lower_is_better=False, source_type="Meta corporativa",
                    source_reference="Umbral interno de soportes documentales.", confidence_level="Alta", created_by="sistema",
                ),
            ])
            session.flush()
        if not session.scalar(select(ImpactSnapshot).where(ImpactSnapshot.organization_id == org.id).limit(1)):
            refresh_impact_snapshot(session, org.id, inventory.id, "sistema")
    session.flush()


def _ensure_v019_defaults(session: Session) -> None:
    """Inicializa riesgos climáticos, controles y hoja de ruta V0.20."""
    _ensure_v018_defaults(session)
    if not settings.seed_demo:
        return
    for org in session.scalars(select(Organization)):
        inventory = session.scalar(select(Inventory).where(Inventory.organization_id == org.id).order_by(Inventory.start_date.desc(), Inventory.id.desc()))
        if inventory and inventory.version == "0.18":
            inventory.version = "0.19"
        assessment = session.scalar(select(ClimateRiskAssessment).where(ClimateRiskAssessment.organization_id == org.id).limit(1))
        if not assessment:
            assessment = ClimateRiskAssessment(
                organization_id=org.id, inventory_id=inventory.id if inventory else None,
                name="Evaluación corporativa de riesgos climáticos 2026", methodology="Análisis corporativo de escenarios",
                scenario="Transición ordenada y estrés físico moderado", base_year=2025, short_horizon=2027,
                medium_horizon=2030, long_horizon=2050, currency="COP", owner="Comité climático",
                status="En tratamiento", notes="Evaluación demostrativa para validar flujos, controles y hoja de ruta.", created_by="sistema",
            )
            session.add(assessment); session.flush()
            risks = [
                ClimateRisk(assessment_id=assessment.id, organization_id=org.id, risk_type="Físico", category="Crónico", hazard="Estrés hídrico y restricciones de abastecimiento", description="Reducción de disponibilidad de agua para procesos y saneamiento.", location="Planta Medellín", value_chain_stage="Operación propia", time_horizon="Mediano plazo", scenario=assessment.scenario, likelihood=4, financial_impact=4, operational_impact=5, reputational_impact=3, inherent_score=20, control_effectiveness=45, residual_score=11, financial_exposure=420000000, owner="Operaciones", response_strategy="Mitigar", response_detail="Balance hídrico, recirculación y fuentes alternativas.", status="En tratamiento", source_reference="Supuesto interno demostrativo; validar con información territorial.", created_by="sistema"),
                ClimateRisk(assessment_id=assessment.id, organization_id=org.id, risk_type="Físico", category="Agudo", hazard="Inundación y afectación logística", description="Interrupción temporal de accesos, bodegas y despachos.", location="Bodega Rionegro", value_chain_stage="Operación propia", time_horizon="Corto plazo", scenario=assessment.scenario, likelihood=3, financial_impact=4, operational_impact=4, reputational_impact=2, inherent_score=12, control_effectiveness=35, residual_score=7.8, financial_exposure=280000000, owner="Logística", response_strategy="Transferir", response_detail="Continuidad, rutas alternas y revisión de pólizas.", status="Abierto", source_reference="Supuesto interno demostrativo; validar mapas y eventos históricos.", created_by="sistema"),
                ClimateRisk(assessment_id=assessment.id, organization_id=org.id, risk_type="Transición", category="Mercado", hazard="Requisitos de huella de carbono de clientes", description="Pérdida de oportunidades comerciales por falta de información verificable y metas.", location="Corporativo", value_chain_stage="Mercado y clientes", time_horizon="Corto plazo", scenario=assessment.scenario, likelihood=4, financial_impact=5, operational_impact=3, reputational_impact=5, inherent_score=20, control_effectiveness=55, residual_score=9, financial_exposure=650000000, owner="Comercial", response_strategy="Mitigar", response_detail="Inventario verificable, fichas de producto y respuesta a clientes.", status="En tratamiento", source_reference="Supuesto comercial demostrativo.", created_by="sistema"),
                ClimateRisk(assessment_id=assessment.id, organization_id=org.id, risk_type="Transición", category="Tecnología", hazard="Obsolescencia energética de equipos", description="Mayor costo operativo y pérdida de competitividad frente a tecnologías eficientes.", location="Planta Medellín", value_chain_stage="Operación propia", time_horizon="Mediano plazo", scenario=assessment.scenario, likelihood=3, financial_impact=4, operational_impact=3, reputational_impact=2, inherent_score=12, control_effectiveness=25, residual_score=9, financial_exposure=310000000, owner="Mantenimiento", response_strategy="Mitigar", response_detail="Plan de renovación y criterios de costo total.", status="Abierto", source_reference="Diagnóstico energético interno demostrativo.", created_by="sistema"),
                ClimateRisk(assessment_id=assessment.id, organization_id=org.id, risk_type="Oportunidad", category="Productos y servicios", hazard="Demanda de soluciones bajas en carbono", description="Crecimiento de ingresos por productos con menor intensidad y circularidad demostrable.", location="Corporativo", value_chain_stage="Mercado y clientes", time_horizon="Mediano plazo", scenario=assessment.scenario, likelihood=4, financial_impact=4, operational_impact=2, reputational_impact=4, inherent_score=16, control_effectiveness=60, residual_score=6.4, financial_exposure=500000000, owner="Innovación", response_strategy="Capturar", response_detail="Desarrollar propuesta de valor y evidencia de impacto.", status="En desarrollo", source_reference="Hipótesis de oportunidad demostrativa.", created_by="sistema"),
            ]
            session.add_all(risks); session.flush()
            session.add_all([
                ClimateRiskControl(risk_id=risks[0].id, organization_id=org.id, name="Programa de eficiencia y recirculación de agua", control_type="Preventivo", owner="Operaciones", status="Operando", effectiveness=45, implementation_date=date(2026, 3, 1), next_review=date(2026, 12, 1), annual_cost=35000000, evidence="Balance hídrico y seguimiento mensual.", created_by="sistema"),
                ClimateRiskControl(risk_id=risks[1].id, organization_id=org.id, name="Plan de continuidad logística", control_type="Correctivo", owner="Logística", status="Implementado", effectiveness=35, implementation_date=date(2026, 5, 15), next_review=date(2026, 11, 15), annual_cost=18000000, evidence="Rutas alternas y proveedores de respaldo.", created_by="sistema"),
                ClimateRiskControl(risk_id=risks[2].id, organization_id=org.id, name="Programa de respuesta climática a clientes", control_type="Preventivo", owner="Comercial", status="Operando", effectiveness=55, implementation_date=date(2026, 6, 1), next_review=date(2026, 10, 1), annual_cost=24000000, evidence="Inventario corporativo y repositorio de evidencias.", created_by="sistema"),
                ClimateRiskControl(risk_id=risks[4].id, organization_id=org.id, name="Comité de innovación baja en carbono", control_type="Estratégico", owner="Innovación", status="Implementado", effectiveness=60, implementation_date=date(2026, 2, 1), next_review=date(2026, 12, 15), annual_cost=30000000, evidence="Portafolio y criterios de priorización.", created_by="sistema"),
            ])
            roadmap = ClimateTransitionRoadmap(organization_id=org.id, assessment_id=assessment.id, name="Hoja de ruta climática 2026–2030", baseline_year=2025, target_year=2030, owner="Comité climático", governance="Revisión trimestral por dirección; responsables funcionales y control anual de supuestos.", approved_budget=980000000, status="En ejecución", notes="Cifras demostrativas; validar antes de decisión de inversión.", created_by="sistema")
            session.add(roadmap); session.flush()
            session.add_all([
                ClimateTransitionAction(roadmap_id=roadmap.id, organization_id=org.id, risk_id=risks[0].id, category="Adaptación", title="Recirculación de agua de proceso", description="Ingeniería, medición y recirculación de corrientes prioritarias.", owner="Operaciones", start_date=date(2026, 4, 1), end_date=date(2027, 3, 31), priority="Alta", status="En ejecución", progress=45, capex=280000000, annual_opex=12000000, annual_savings=65000000, avoided_loss=90000000, indicator="Consumo específico de agua", target_value=20, current_value=8, unit="% reducción", dependencies="Estudio de ingeniería y permisos internos.", created_by="sistema"),
                ClimateTransitionAction(roadmap_id=roadmap.id, organization_id=org.id, risk_id=risks[3].id, category="Descarbonización", title="Renovación de motores y control de demanda", description="Sustitución priorizada de equipos y gestión de picos.", owner="Mantenimiento", start_date=date(2026, 8, 1), end_date=date(2028, 6, 30), priority="Alta", status="Planeada", progress=15, expected_reduction_tco2e=180, capex=420000000, annual_opex=8000000, annual_savings=115000000, avoided_loss=40000000, indicator="Consumo eléctrico específico", target_value=12, current_value=2, unit="% reducción", dependencies="Auditoría energética y aprobación CAPEX.", created_by="sistema"),
                ClimateTransitionAction(roadmap_id=roadmap.id, organization_id=org.id, risk_id=risks[2].id, category="Mercado", title="Paquete de información climática para clientes", description="Huella corporativa, trazabilidad y respuestas comerciales controladas.", owner="Comercial", start_date=date(2026, 5, 1), end_date=date(2026, 11, 30), priority="Alta", status="En ejecución", progress=60, capex=55000000, annual_opex=18000000, annual_savings=0, avoided_loss=220000000, indicator="Solicitudes respondidas a tiempo", target_value=95, current_value=72, unit="%", dependencies="Cierre del inventario y control documental.", created_by="sistema"),
                ClimateTransitionAction(roadmap_id=roadmap.id, organization_id=org.id, risk_id=risks[4].id, category="Oportunidad", title="Línea de productos con evidencia de impacto", description="Definición de criterios, medición y narrativa comercial verificable.", owner="Innovación", start_date=date(2026, 9, 1), end_date=date(2028, 12, 31), priority="Media", status="Planeada", progress=10, expected_reduction_tco2e=350, capex=190000000, annual_opex=35000000, annual_savings=160000000, avoided_loss=0, indicator="Ingresos de portafolio bajo en carbono", target_value=15, current_value=1, unit="% de ingresos", dependencies="Metodología de producto y validación comercial.", created_by="sistema"),
            ])
    session.flush()



def _ensure_v020_defaults(session: Session) -> None:
    """Inicializa comparación de escenarios, divulgación y comité directivo V0.20."""
    _ensure_v019_defaults(session)
    if not settings.seed_demo:
        return
    for org in session.scalars(select(Organization)):
        inventory = session.scalar(
            select(Inventory).where(Inventory.organization_id == org.id)
            .order_by(Inventory.start_date.desc(), Inventory.id.desc())
        )
        if inventory and inventory.version == "0.19":
            inventory.version = "0.20"
        assessment = session.scalar(
            select(ClimateRiskAssessment).where(ClimateRiskAssessment.organization_id == org.id)
            .order_by(ClimateRiskAssessment.updated_at.desc(), ClimateRiskAssessment.id.desc())
        )
        if not session.scalar(select(ClimateScenarioDefinition).where(ClimateScenarioDefinition.organization_id == org.id).limit(1)):
            session.add_all([
                ClimateScenarioDefinition(
                    organization_id=org.id, assessment_id=assessment.id if assessment else None,
                    name="Transición ordenada", code="ORD-2030", scenario_type="Transición",
                    temperature_pathway="1,5–2 °C", physical_multiplier=0.85, transition_multiplier=1.25,
                    opportunity_multiplier=1.30, carbon_price_2030=180000, energy_cost_change_pct=8,
                    demand_change_pct=12, probability_weight=40,
                    narrative="Políticas graduales, inversión temprana y mayor demanda por soluciones bajas en carbono.",
                    source_reference="Supuesto corporativo demostrativo; documentar fuente y calibración antes de uso externo.", created_by="sistema",
                ),
                ClimateScenarioDefinition(
                    organization_id=org.id, assessment_id=assessment.id if assessment else None,
                    name="Transición tardía y abrupta", code="TAR-2030", scenario_type="Transición",
                    temperature_pathway="Ajuste acelerado", physical_multiplier=1.10, transition_multiplier=1.55,
                    opportunity_multiplier=1.05, carbon_price_2030=320000, energy_cost_change_pct=18,
                    demand_change_pct=-5, probability_weight=35,
                    narrative="La acción se retrasa y luego exige cambios regulatorios, tecnológicos y financieros rápidos.",
                    source_reference="Supuesto corporativo demostrativo; documentar fuente y calibración antes de uso externo.", created_by="sistema",
                ),
                ClimateScenarioDefinition(
                    organization_id=org.id, assessment_id=assessment.id if assessment else None,
                    name="Altas emisiones y estrés físico", code="FIS-2050", scenario_type="Físico",
                    temperature_pathway=">3 °C", physical_multiplier=1.65, transition_multiplier=0.90,
                    opportunity_multiplier=0.80, carbon_price_2030=80000, energy_cost_change_pct=22,
                    demand_change_pct=-8, probability_weight=25,
                    narrative="Menor coordinación de transición y mayor materialización de amenazas físicas sobre activos y cadena de valor.",
                    source_reference="Supuesto corporativo demostrativo; validar con información sectorial y territorial.", created_by="sistema",
                ),
            ])
        statement = session.scalar(
            select(ClimateDisclosureStatement).where(ClimateDisclosureStatement.organization_id == org.id)
            .order_by(ClimateDisclosureStatement.updated_at.desc(), ClimateDisclosureStatement.id.desc())
        )
        if not statement:
            statement = ClimateDisclosureStatement(
                organization_id=org.id, inventory_id=inventory.id if inventory else None,
                title="Divulgación climática corporativa 2025", framework="Marco corporativo compatible con divulgaciones climáticas",
                reporting_period="2025", scope_description="Operación corporativa, inventario GEI, riesgos, oportunidades, métricas, metas y plan de transición.",
                materiality_basis="Priorización por impacto financiero, operativo, reputacional y relevancia para grupos de interés.",
                owner="Comité climático", status="En preparación",
                notes="La compatibilidad no equivale a cumplimiento certificado de un estándar externo.", created_by="sistema",
            )
            session.add(statement); session.flush()
            specs = [
                ("Gobernanza", "GOV-01", "Describir la supervisión del órgano de gobierno sobre riesgos y oportunidades climáticas.", "El comité directivo recibe seguimiento trimestral y aprueba presupuesto, apetito de riesgo y decisiones materiales.", "Completo", "Acta de comité y hoja de ruta", "Secretaría general"),
                ("Gobernanza", "GOV-02", "Describir las responsabilidades de la administración y los mecanismos de rendición de cuentas.", "Existe responsable ejecutivo, dueños funcionales y seguimiento mediante compromisos trazables.", "Completo", "Matriz de responsables", "Gerencia"),
                ("Estrategia", "EST-01", "Explicar riesgos y oportunidades relevantes en horizontes corto, medio y largo.", "La evaluación corporativa identifica amenazas físicas, de transición y oportunidades por horizonte.", "Completo", "Evaluación de riesgos climáticos", "Dirección ambiental"),
                ("Estrategia", "EST-02", "Explicar efectos actuales y previstos sobre modelo de negocio, cadena de valor y finanzas.", "Se documentaron exposiciones y oportunidades; falta validar sensibilidad financiera con presupuesto aprobado.", "Parcial", "Comparación de escenarios", "Finanzas"),
                ("Estrategia", "EST-03", "Describir resiliencia de la estrategia bajo escenarios climáticos diferentes.", "Se comparan tres escenarios y se calcula presión financiera, exposición y puntuación de resiliencia.", "Parcial", "Módulo de escenarios V0.20", "Planeación"),
                ("Riesgos", "RSK-01", "Describir procesos para identificar, evaluar, priorizar y monitorear riesgos climáticos.", "La matriz 5×5, los controles y la hoja de ruta conservan responsables, evidencia y revisión.", "Completo", "Registro de riesgos y controles", "Gestión de riesgos"),
                ("Riesgos", "RSK-02", "Explicar integración con el sistema general de gestión de riesgos.", "La integración se encuentra definida conceptualmente y requiere formalización en la matriz corporativa.", "Parcial", "Procedimiento de riesgos", "Gestión de riesgos"),
                ("Métricas y metas", "MET-01", "Presentar emisiones de alcance 1, 2 y 3 y metodología aplicable.", "El inventario reporta emisiones por alcance con factores, GWP, evidencias y trazabilidad de cálculo.", "Completo", "Informe técnico y memoria de cálculo", "Dirección ambiental"),
                ("Métricas y metas", "MET-02", "Presentar métricas de riesgo, oportunidad, capital desplegado y desempeño.", "La plataforma consolida exposición residual, CAPEX, OPEX, ahorros, pérdidas evitadas y avance.", "Completo", "Inteligencia de impacto y riesgos", "Finanzas"),
                ("Métricas y metas", "MET-03", "Describir metas climáticas, línea base, periodo y progreso.", "Las metas y la trayectoria están registradas; falta aprobación final del comité.", "Parcial", "Metas y escenarios de reducción", "Comité climático"),
                ("Plan de transición", "TRN-01", "Explicar acciones, recursos, dependencias y mecanismos de seguimiento.", "La hoja de ruta contiene acciones, presupuesto, responsables, indicadores, dependencias y evidencias.", "Completo", "Hoja de ruta climática 2026–2030", "Comité climático"),
                ("Controles de reporte", "CTL-01", "Definir revisión, aprobación, control documental y limitaciones de la divulgación.", "Se aplica revisión por roles, registro documental, hash y advertencias sobre supuestos demostrativos.", "Parcial", "Control, documentos y paquete de comité", "Revisor"),
            ]
            for pillar, code, requirement, response, status, evidence, owner in specs:
                session.add(ClimateDisclosureRequirement(
                    statement_id=statement.id, organization_id=org.id, pillar=pillar, code=code,
                    requirement=requirement, response=response, status=status, evidence_reference=evidence,
                    owner=owner, due_date=date(2026, 12, 15), updated_by="sistema",
                ))
        briefing = session.scalar(
            select(ClimateBoardBriefing).where(ClimateBoardBriefing.organization_id == org.id)
            .order_by(ClimateBoardBriefing.updated_at.desc(), ClimateBoardBriefing.id.desc())
        )
        if not briefing:
            briefing = ClimateBoardBriefing(
                organization_id=org.id, assessment_id=assessment.id if assessment else None,
                disclosure_id=statement.id if statement else None,
                title="Informe climático para comité directivo · 2026", meeting_date=date(2026, 9, 15),
                audience="Comité directivo", status="Preparado",
                executive_summary="La organización cuenta con inventario trazable, riesgos priorizados y hoja de ruta. Las decisiones críticas se concentran en resiliencia hídrica, eficiencia energética y cierre de brechas de divulgación.",
                decisions_required="Aprobar inversiones prioritarias, validar apetito de riesgo y autorizar la publicación controlada de información climática.",
                key_message="Actuar temprano reduce exposición, protege ingresos y mejora la calidad de respuesta a clientes y financiadores.",
                prepared_by="Dirección ambiental", created_by="sistema",
            )
            session.add(briefing); session.flush()
            session.add_all([
                ClimateBoardDecision(
                    briefing_id=briefing.id, organization_id=org.id, topic="Recirculación de agua de proceso",
                    decision="Aprobar la fase de ingeniería y reservar CAPEX sujeto a validación técnica.", owner="Operaciones y Finanzas",
                    due_date=date(2026, 10, 15), status="Pendiente", rationale="Es la principal respuesta al riesgo físico residual identificado.",
                    evidence_reference="Hoja de ruta · acción de adaptación", created_by="sistema",
                ),
                ClimateBoardDecision(
                    briefing_id=briefing.id, organization_id=org.id, topic="Auditoría energética y renovación de motores",
                    decision="Autorizar auditoría energética para estructurar el caso de inversión 2027–2028.", owner="Mantenimiento",
                    due_date=date(2026, 11, 30), status="En análisis", rationale="Reduce exposición tecnológica, consumo y costo de carbono futuro.",
                    evidence_reference="Hoja de ruta · descarbonización", created_by="sistema",
                ),
                ClimateBoardDecision(
                    briefing_id=briefing.id, organization_id=org.id, topic="Divulgación climática a terceros",
                    decision="Aprobar publicación únicamente después de completar revisión jurídica y metodológica.", owner="Gerencia y Revisor",
                    due_date=date(2026, 12, 15), status="Pendiente", rationale="Evita presentar supuestos internos como datos verificados o compromisos definitivos.",
                    evidence_reference="Matriz de divulgación", created_by="sistema",
                ),
            ])
    session.flush()


def _ensure_v021_defaults(session: Session) -> None:
    """Seed V1.0 consolidation controls without changing inventory results."""
    for inventory in session.scalars(select(Inventory)):
        if inventory.version == "0.20":
            inventory.version = "0.21"
    finding_specs = [
        ("TD-001", "Arquitectura", "Dividir el controlador principal por dominios", "app/main.py concentra rutas y lógica de presentación; migrar progresivamente a routers y servicios.", "Crítica", "En curso", "Arquitectura", "V0.22"),
        ("TD-002", "Arquitectura", "Separar modelos de base de datos por dominio", "app/database.py concentra el modelo completo; definir módulos declarativos y repositorios por contexto.", "Alta", "Abierto", "Arquitectura", "V0.23"),
        ("TD-003", "Pruebas", "Distribuir pruebas por dominio", "La suite histórica sigue concentrada en test_app.py; V0.21 inicia una suite independiente para consolidación.", "Media", "En curso", "Calidad", "V0.22"),
        ("SEC-001", "Seguridad", "Incorporar protección CSRF explícita", "Todos los formularios mutables deben exigir token CSRF o una política equivalente verificada.", "Crítica", "Abierto", "Seguridad", "V0.24"),
        ("SEC-002", "Seguridad", "Persistir rate limiting y bloqueo de acceso", "Mover el estado de bloqueo desde memoria del proceso a un backend compartido.", "Alta", "Abierto", "Seguridad", "V0.24"),
        ("MET-001", "Metodología", "Construir biblioteca oficial de factores", "Reemplazar factores demostrativos por factores documentados, versionados y aprobados por periodo y geografía.", "Crítica", "Abierto", "Comité metodológico", "V0.22"),
        ("MET-002", "Metodología", "Validar casos patrón del motor", "Crear resultados esperados independientes para unidades, gases, GWP, alcance 2, biogénico, remociones y recalculo.", "Crítica", "Abierto", "Comité metodológico", "V0.22"),
        ("UX-001", "Experiencia", "Validar recorridos completos por rol", "Ejecutar pruebas observadas con cliente, consultor, revisor, directivo y verificador.", "Alta", "En curso", "Producto", "V0.23"),
        ("OPS-001", "Operación", "Implementar CI/CD y calidad automatizada", "Ejecutar pruebas, lint, análisis de dependencias y migraciones en cada cambio.", "Alta", "Abierto", "DevOps", "V0.24"),
        ("OPS-002", "Operación", "Ensayar restauración y continuidad", "Documentar RPO/RTO y comprobar restauración completa con evidencias e informes.", "Alta", "Abierto", "Operaciones", "V0.24"),
        ("LEG-001", "Legal", "Cerrar documentos jurídicos del SaaS", "Términos, privacidad, DPA, contrato SaaS, SLA, retención y limitaciones metodológicas.", "Media", "Abierto", "Jurídica", "V0.25"),
        ("BRD-001", "Marca", "Validar marca, dominio y activos digitales", "Realizar búsqueda de antecedentes y reservar activos antes del lanzamiento público.", "Media", "Abierto", "Dirección", "V0.25"),
        ("PIL-001", "Piloto", "Ejecutar piloto real Greenatics", "Cargar Yarumal y Támesis, contrastar con memoria independiente y registrar incidencias.", "Crítica", "Abierto", "Equipo piloto", "V0.23"),
    ]
    gate_specs = [
        ("GATE-ARCH", "Arquitectura", "Arquitectura modular revisable", "Parcial", "Arquitectura"),
        ("GATE-METH", "Metodología", "Metodología y biblioteca oficial aprobadas", "Pendiente", "Comité metodológico"),
        ("GATE-CALC", "Cálculo", "Casos patrón y motor matemático validados", "Pendiente", "Comité metodológico"),
        ("GATE-SEC", "Seguridad", "Auditoría de seguridad sin hallazgos críticos", "Pendiente", "Seguridad"),
        ("GATE-UX", "Experiencia", "Recorridos por rol completados sin bloqueos", "Parcial", "Producto"),
        ("GATE-PILOT", "Piloto", "Inventario Greenatics contrastado y aprobado", "Pendiente", "Equipo piloto"),
        ("GATE-LEGAL", "Legal", "Documentación contractual y de privacidad aprobada", "Pendiente", "Jurídica"),
        ("GATE-OPS", "Operación", "Despliegue, monitoreo y restauración verificados", "Parcial", "DevOps"),
        ("GATE-MARKET", "Mercado", "Oferta y precio validados con clientes piloto", "Pendiente", "Dirección comercial"),
    ]
    journey_specs = [
        ("JRN-AMBIENTAL", "Cliente"), ("JRN-CONSULTOR", "Consultor"),
        ("JRN-REVISOR", "Revisor"), ("JRN-DIRECTIVO", "Administrador"),
        ("JRN-VERIFICADOR", "Verificador"),
    ]
    for org in session.scalars(select(Organization)):
        for code, area, title, detail, priority, status, owner, target in finding_specs:
            exists = session.scalar(select(ConsolidationFinding).where(ConsolidationFinding.organization_id == org.id, ConsolidationFinding.code == code))
            if not exists:
                session.add(ConsolidationFinding(organization_id=org.id, code=code, area=area, title=title, detail=detail, priority=priority, status=status, owner=owner, target_version=target))
        for code, category, name, status, responsible in gate_specs:
            exists = session.scalar(select(ReleaseGate).where(ReleaseGate.organization_id == org.id, ReleaseGate.code == code))
            if not exists:
                session.add(ReleaseGate(organization_id=org.id, code=code, category=category, name=name, status=status, responsible=responsible))
        for code, role in journey_specs:
            exists = session.scalar(select(JourneyValidation).where(JourneyValidation.organization_id == org.id, JourneyValidation.journey_code == code))
            if not exists:
                session.add(JourneyValidation(organization_id=org.id, journey_code=code, role=role, status="No probado"))
        if settings.seed_demo:
            consultant = session.scalar(select(AppUser).where(AppUser.organization_id == org.id, AppUser.role == "Consultor"))
            existing_notice = session.scalar(select(Notification).where(Notification.organization_id == org.id, Notification.title == "Consolidación V1.0 disponible"))
            if consultant and not existing_notice:
                session.add(Notification(organization_id=org.id, user_id=consultant.id, title="Consolidación V1.0 disponible", message="La V0.21 centraliza deuda, puertas de salida, permisos y recorridos de validación.", link="/consolidacion", category="Producto", priority="Alta", status="Entregada"))
    session.flush()


def _ensure_v022_defaults(session: Session) -> None:
    """Initialize the documented methodology core and reference validation suite."""
    for inventory in session.scalars(select(Inventory)):
        if inventory.version == "0.21":
            inventory.version = "0.22"
    from .methodology_core import ensure_methodology_core_defaults, run_reference_suite

    ensure_methodology_core_defaults(session)
    existing_run = session.scalar(select(MethodologyValidationRun).where(MethodologyValidationRun.engine_version.in_(["0.22.0", "0.23.0", "0.28.0"])).limit(1))
    if not existing_run:
        run_reference_suite(session, "sistema · instalación V0.22")
    if settings.seed_demo:
        for org in session.scalars(select(Organization)):
            consultant = session.scalar(select(AppUser).where(AppUser.organization_id == org.id, AppUser.role == "Consultor"))
            existing_notice = session.scalar(select(Notification).where(Notification.organization_id == org.id, Notification.title == "Núcleo metodológico V0.22 disponible"))
            if consultant and not existing_notice:
                session.add(Notification(
                    organization_id=org.id, user_id=consultant.id,
                    title="Núcleo metodológico V0.22 disponible",
                    message="Se incorporaron fuentes documentales, factor UPME SIN 2024, GWP versionados, reglas de selección y casos patrón reproducibles.",
                    link="/metodologia/nucleo", category="Metodología", priority="Alta", status="Entregada",
                ))
    session.flush()



def _ensure_v023_defaults(session: Session) -> None:
    """Initialize the sector library and Greenatics pilot readiness matrix."""
    for inventory in session.scalars(select(Inventory)):
        if inventory.version in {"0.20", "0.21", "0.22"}:
            inventory.version = "0.23"
    from .sector_library import ensure_sector_library_defaults
    from .methodology_core import run_reference_suite

    ensure_sector_library_defaults(session)
    existing_run = session.scalar(
        select(MethodologyValidationRun)
        .where(MethodologyValidationRun.engine_version == "0.28.0")
        .order_by(MethodologyValidationRun.id.desc())
        .limit(1)
    )
    if not existing_run or existing_run.total_cases < 20:
        run_reference_suite(session, "sistema · instalación V0.28")
    session.flush()

def _ensure_v024_defaults(session: Session) -> None:
    """Backfill the audit integrity chain and move active inventories to V0.24."""
    for inventory in session.scalars(select(Inventory)):
        if inventory.version in {"0.20", "0.21", "0.22", "0.23"}:
            inventory.version = "0.24"
    backfill_audit_chain(session)
    session.flush()



def _ensure_v025_defaults(session: Session) -> None:
    """Prepare the guided beta and controlled pilot execution without starting it automatically."""
    for inventory in session.scalars(select(Inventory)):
        if inventory.version in {"0.20", "0.21", "0.22", "0.23", "0.24"}:
            inventory.version = "0.25"
    for finding in session.scalars(select(ConsolidationFinding).where(ConsolidationFinding.code == "PIL-001")).all():
        finding.status = "En curso"
        finding.target_version = "V0.25"
        finding.evidence = "V0.25 convierte la matriz Greenatics en inventario operativo, solicitudes, captura masiva, incidencias y contraste independiente. El cierre requiere datos reales y factores pendientes aprobados."
    for gate in session.scalars(select(ReleaseGate).where(ReleaseGate.code.in_(["GATE-UX", "GATE-PILOT"]))).all():
        gate.status = "Parcial"
        gate.evidence = "Centro de trabajo guiado y ejecución controlada del piloto disponibles en V0.25."
        gate.notes = "La puerta permanece parcial hasta completar los datos reales, cerrar incidencias y aprobar el contraste independiente."
    if settings.seed_demo:
        for org in session.scalars(select(Organization)).all():
            consultant = session.scalar(select(AppUser).where(AppUser.organization_id == org.id, AppUser.role == "Consultor"))
            existing_notice = session.scalar(select(Notification).where(Notification.organization_id == org.id, Notification.title == "Beta guiada V0.25 disponible"))
            if consultant and not existing_notice:
                session.add(Notification(
                    organization_id=org.id,
                    user_id=consultant.id,
                    title="Beta guiada V0.25 disponible",
                    message="El dashboard prioriza la próxima acción y el piloto Greenatics puede ejecutarse como inventario controlado con contraste independiente.",
                    link="/piloto-greenatics/ejecucion",
                    category="Producto",
                    priority="Alta",
                    status="Entregada",
                ))
    session.flush()


def _ensure_v026_defaults(session: Session) -> None:
    """Enable controlled real-data intake and quality gates for the Greenatics pilot."""
    for inventory in session.scalars(select(Inventory)):
        if inventory.version in {"0.20", "0.21", "0.22", "0.23", "0.24", "0.25"}:
            inventory.version = "0.26"
    for finding in session.scalars(select(ConsolidationFinding).where(ConsolidationFinding.code == "PIL-001")).all():
        finding.status = "En curso"
        finding.target_version = "V0.26"
        finding.evidence = "V0.26 incorpora validación previa, lotes idempotentes, hallazgos de calidad, control de unidades, duplicados, atípicos y aplicación auditada al inventario."
    for gate in session.scalars(select(ReleaseGate).where(ReleaseGate.code.in_(["GATE-DATA", "GATE-PILOT"]))).all():
        gate.status = "Parcial"
        gate.evidence = "Centro de calidad de datos y aplicación controlada de lotes disponibles en V0.26."
        gate.notes = "La puerta permanece parcial hasta cargar información real completa, cerrar hallazgos y validar evidencias primarias."
    if settings.seed_demo:
        for org in session.scalars(select(Organization)).all():
            consultant = session.scalar(select(AppUser).where(AppUser.organization_id == org.id, AppUser.role == "Consultor"))
            existing_notice = session.scalar(select(Notification).where(Notification.organization_id == org.id, Notification.title == "Control de datos V0.26 disponible"))
            if consultant and not existing_notice:
                session.add(Notification(
                    organization_id=org.id,
                    user_id=consultant.id,
                    title="Control de datos V0.26 disponible",
                    message="Valida archivos reales antes de aplicarlos al piloto: periodos, unidades, duplicados, evidencia, estimaciones y valores atípicos.",
                    link="/calidad-datos",
                    category="Datos",
                    priority="Alta",
                    status="Entregada",
                ))
    session.flush()

def _ensure_v027_defaults(session: Session) -> None:
    """Enable monthly reconciliation and immutable period closing."""
    for inventory in session.scalars(select(Inventory)):
        if inventory.version in {"0.20", "0.21", "0.22", "0.23", "0.24", "0.25", "0.26"}:
            inventory.version = "0.27"
    for finding in session.scalars(select(ConsolidationFinding).where(ConsolidationFinding.code == "PIL-001")).all():
        finding.status = "En curso"
        finding.target_version = "V0.27"
        finding.evidence = "V0.27 incorpora conciliación mensual por fuente, puertas de datos y metodología, revisión, cierre con instantánea SHA-256 y reapertura auditada."
    for gate in session.scalars(select(ReleaseGate).where(ReleaseGate.code.in_(["GATE-DATA", "GATE-PILOT", "GATE-CALC"]))).all():
        gate.status = "Parcial"
        gate.evidence = "Cierre mensual V0.27 disponible con cobertura, evidencia, factores, cálculos y hash reproducible."
        gate.notes = "La puerta permanece parcial hasta completar factores pendientes y ejecutar cierres con información real de Greenatics."
    if settings.seed_demo:
        for org in session.scalars(select(Organization)).all():
            consultant = session.scalar(select(AppUser).where(AppUser.organization_id == org.id, AppUser.role == "Consultor"))
            existing_notice = session.scalar(select(Notification).where(Notification.organization_id == org.id, Notification.title == "Cierre mensual V0.27 disponible"))
            if consultant and not existing_notice:
                session.add(Notification(
                    organization_id=org.id,
                    user_id=consultant.id,
                    title="Cierre mensual V0.27 disponible",
                    message="Concilia cada periodo por fuente, envíalo a revisión y congélalo con un hash reproducible cuando no existan bloqueos.",
                    link="/cierre-mensual",
                    category="Control",
                    priority="Alta",
                    status="Entregada",
                ))
    session.flush()


def _ensure_v028_defaults(session: Session) -> None:
    """Load the controlled Colombian factor library and sector calculators."""
    for inventory in session.scalars(select(Inventory)):
        if inventory.version in {"0.20", "0.21", "0.22", "0.23", "0.24", "0.25", "0.26", "0.27"}:
            inventory.version = "0.28"
    from .sector_library import ensure_sector_library_defaults
    from .methodology_core import run_reference_suite

    ensure_sector_library_defaults(session)
    existing_run = session.scalar(
        select(MethodologyValidationRun)
        .where(MethodologyValidationRun.engine_version == "0.28.0")
        .order_by(MethodologyValidationRun.id.desc())
        .limit(1)
    )
    if not existing_run or existing_run.total_cases < 20:
        run_reference_suite(session, "sistema · instalación V0.28")
    for finding in session.scalars(select(ConsolidationFinding).where(ConsolidationFinding.code == "MET-001")).all():
        finding.status = "En curso"
        finding.target_version = "V0.28"
        finding.evidence = "Biblioteca Colombia V0.28: combustibles condicionados, métodos de aguas residuales, fertilización nitrogenada y balance operativo de biogás, con 20 casos patrón."
    # Completar los nuevos campos de trazabilidad en cálculos migrados sin
    # alterar el resultado, el factor ni la versión histórica del motor.
    for calculation in session.scalars(select(EmissionCalculation)).all():
        record = calculation.activity_data
        source = record.source
        factor_uncertainty = max(float(calculation.factor_version.uncertainty_percentage or 0), 0.0)
        activity_uncertainty = max(float(record.uncertainty_percentage or 0), 0.0)
        combined = math.sqrt(activity_uncertainty ** 2 + factor_uncertainty ** 2)
        calculation.reporting_bucket = source.accounting_treatment or "Emisión bruta"
        calculation.uncertainty_percentage = combined
        calculation.lower_co2e_kg = max(0.0, calculation.co2e_kg * (1 - combined / 100))
        calculation.upper_co2e_kg = calculation.co2e_kg * (1 + combined / 100)

    for gate in session.scalars(select(ReleaseGate).where(ReleaseGate.code.in_(["GATE-METH", "GATE-CALC", "GATE-PILOT"]))).all():
        gate.status = "Parcial"
        gate.evidence = "V0.28 incorpora biblioteca colombiana controlada y calculadoras sectoriales reproducibles."
        gate.notes = "Pendiente validar FECOC primaria, parámetros reales de planta y transporte por tecnología antes de V1.0."
    if settings.seed_demo:
        for org in session.scalars(select(Organization)).all():
            consultant = session.scalar(select(AppUser).where(AppUser.organization_id == org.id, AppUser.role == "Consultor"))
            existing_notice = session.scalar(select(Notification).where(Notification.organization_id == org.id, Notification.title == "Biblioteca Colombia V0.28 disponible"))
            if consultant and not existing_notice:
                session.add(Notification(
                    organization_id=org.id,
                    user_id=consultant.id,
                    title="Biblioteca Colombia V0.28 disponible",
                    message="Calcula combustibles, carga orgánica de aguas residuales, N aplicado al suelo y balance de biogás con restricciones metodológicas visibles.",
                    link="/metodologia/colombia",
                    category="Metodología",
                    priority="Alta",
                    status="Entregada",
                ))
    session.flush()


def _ensure_v030_defaults(session: Session) -> None:
    """Enable configurable operational imports without replacing prior modules."""
    for inventory in session.scalars(select(Inventory)):
        if inventory.version in {"0.20", "0.21", "0.22", "0.23", "0.24", "0.25", "0.26", "0.27", "0.28", "0.29"}:
            inventory.version = "0.30"
    for gate in session.scalars(
        select(ReleaseGate).where(ReleaseGate.code.in_(["GATE-DATA", "GATE-PILOT"]))
    ).all():
        gate.status = "Parcial"
        gate.evidence = "V0.30 conserva las cargas operativas y añade instalación, actualización y limpieza segura en macOS con datos persistentes fuera del código."
        gate.notes = "La puerta permanece parcial hasta ejecutar cargas reales completas, resolver hallazgos y validar soportes primarios."
    if settings.seed_demo:
        for org in session.scalars(select(Organization)).all():
            consultant = session.scalar(
                select(AppUser).where(AppUser.organization_id == org.id, AppUser.role == "Consultor")
            )
            existing_notice = session.scalar(
                select(Notification).where(
                    Notification.organization_id == org.id,
                    Notification.title == "Instalación segura V0.30 disponible",
                )
            )
            if consultant and not existing_notice:
                session.add(Notification(
                    organization_id=org.id,
                    user_id=consultant.id,
                    title="Instalación segura V0.30 disponible",
                    message="La aplicación ahora se instala o actualiza con doble clic, conserva los datos fuera del código y respalda antes de retirar versiones antiguas.",
                    link="/modulos",
                    category="Plataforma",
                    priority="Alta",
                    status="Entregada",
                ))
    session.flush()


def _ensure_v031_defaults(session: Session) -> None:
    """Mark the product-consolidation release without changing the data model."""
    for inventory in session.scalars(select(Inventory)):
        if inventory.version in {"0.20", "0.21", "0.22", "0.23", "0.24", "0.25", "0.26", "0.27", "0.28", "0.29", "0.30"}:
            inventory.version = "0.31"
    for gate in session.scalars(
        select(ReleaseGate).where(ReleaseGate.code.in_(["GATE-UX", "GATE-PILOT", "GATE-OPS"]))
    ).all():
        gate.status = "Parcial"
        gate.evidence = "V0.31 organiza la plataforma por rol, separa el flujo esencial de las capacidades avanzadas y crea un recorrido único del inventario."
        gate.notes = "Pendiente validar el recorrido completo con usuarios reales de Greenatics y clientes piloto antes de aprobar la puerta."
    if settings.seed_demo:
        for org in session.scalars(select(Organization)).all():
            consultant = session.scalar(
                select(AppUser).where(AppUser.organization_id == org.id, AppUser.role == "Consultor")
            )
            existing_notice = session.scalar(
                select(Notification).where(
                    Notification.organization_id == org.id,
                    Notification.title == "Experiencia por rol V0.31 disponible",
                )
            )
            if consultant and not existing_notice:
                session.add(Notification(
                    organization_id=org.id,
                    user_id=consultant.id,
                    title="Experiencia por rol V0.31 disponible",
                    message="La vista esencial prioriza el recorrido del inventario; la vista completa conserva módulos avanzados e internos.",
                    link="/recorrido-inventario",
                    category="Producto",
                    priority="Alta",
                    status="Entregada",
                ))
    session.flush()


def _ensure_v032_defaults(session: Session) -> None:
    """Close methodological governance without altering historical calculations."""
    for inventory in session.scalars(select(Inventory)):
        if inventory.version in {"0.20", "0.21", "0.22", "0.23", "0.24", "0.25", "0.26", "0.27", "0.28", "0.29", "0.30", "0.31"}:
            inventory.version = "0.32"
        for source in inventory.sources:
            if not source.accounting_treatment:
                source.accounting_treatment = "Emisión bruta"
            if source.scope == 2 and source.scope2_method == "No aplica" and settings.seed_demo and source.name.casefold() == "electricidad":
                source.scope2_method = "Location-based"
            elif source.scope != 2:
                source.scope2_method = "No aplica"
        if settings.seed_demo:
            uncertainty_by_quality = {"A": 5.0, "B": 10.0, "C": 20.0, "D": 40.0}
            for source in inventory.sources:
                for record in source.activity_records:
                    if record.uncertainty_percentage <= 0:
                        record.uncertainty_percentage = uncertainty_by_quality.get(record.quality_level, 25.0)
                        record.uncertainty_basis = record.uncertainty_basis or f"Valor demostrativo por calidad {record.quality_level}"
    # Completar los nuevos campos de trazabilidad en cálculos migrados sin
    # alterar el resultado, el factor ni la versión histórica del motor.
    for calculation in session.scalars(select(EmissionCalculation)).all():
        record = calculation.activity_data
        source = record.source
        factor_uncertainty = max(float(calculation.factor_version.uncertainty_percentage or 0), 0.0)
        activity_uncertainty = max(float(record.uncertainty_percentage or 0), 0.0)
        combined = math.sqrt(activity_uncertainty ** 2 + factor_uncertainty ** 2)
        calculation.reporting_bucket = source.accounting_treatment or "Emisión bruta"
        calculation.uncertainty_percentage = combined
        calculation.lower_co2e_kg = max(0.0, calculation.co2e_kg * (1 - combined / 100))
        calculation.upper_co2e_kg = calculation.co2e_kg * (1 + combined / 100)

    for gate in session.scalars(select(ReleaseGate).where(ReleaseGate.code.in_(["GATE-METH", "GATE-CALC", "GATE-PILOT"]))).all():
        gate.status = "Parcial"
        gate.evidence = "V0.32 separa emisiones brutas, biogénicas, remociones, evitadas y compensaciones; incorpora incertidumbre y recalculo del año base."
        gate.notes = "Pendiente aprobación independiente de políticas y validación con datos reales antes de V1.0."
    if settings.seed_demo:
        for org in session.scalars(select(Organization)).all():
            consultant = session.scalar(select(AppUser).where(AppUser.organization_id == org.id, AppUser.role == "Consultor"))
            existing_notice = session.scalar(select(Notification).where(Notification.organization_id == org.id, Notification.title == "Cierre metodológico V0.32 disponible"))
            if consultant and not existing_notice:
                session.add(Notification(organization_id=org.id, user_id=consultant.id, title="Cierre metodológico V0.32 disponible", message="Clasifica partidas, documenta incertidumbre, controla alcance 2 y evalúa recalculos del año base.", link="/metodologia/cierre", category="Metodología", priority="Alta", status="Entregada"))
    session.flush()



def _ensure_v033_defaults(session: Session) -> None:
    """Activate the controlled Greenatics pilot without fabricating operational data."""
    for inventory in session.scalars(select(Inventory)):
        if inventory.version in {"0.20", "0.21", "0.22", "0.23", "0.24", "0.25", "0.26", "0.27", "0.28", "0.29", "0.30", "0.31", "0.32"}:
            inventory.version = "0.33"
    for gate in session.scalars(select(ReleaseGate).where(ReleaseGate.code.in_(["GATE-PILOT", "GATE-UX", "GATE-CALC"]))):
        gate.status = "Parcial"
        gate.evidence = "V0.33 controla el piloto Greenatics por sede, fuente, mes, evidencia y contraste independiente."
        gate.notes = "La puerta solo podrá aprobarse después de cargar soportes reales, completar cobertura anual y cerrar diferencias por fuente."
    if settings.seed_demo:
        for org in session.scalars(select(Organization)).all():
            consultant = session.scalar(select(AppUser).where(AppUser.organization_id == org.id, AppUser.role == "Consultor"))
            title = "Centro de control del piloto Greenatics V0.33"
            existing = session.scalar(select(Notification).where(Notification.organization_id == org.id, Notification.title == title))
            if consultant and not existing:
                session.add(Notification(organization_id=org.id, user_id=consultant.id, title=title, message="Controla cobertura mensual, evidencias y contraste fuente a fuente sin aplicar datos de referencia automáticamente.", link="/piloto-greenatics/ejecucion", category="Piloto", priority="Alta", status="Entregada"))
    session.flush()

def _ensure_v034_defaults(session: Session) -> None:
    """Register operational hardening without claiming production readiness."""
    for inventory in session.scalars(select(Inventory)):
        if inventory.version in {"0.20", "0.21", "0.22", "0.23", "0.24", "0.25", "0.26", "0.27", "0.28", "0.29", "0.30", "0.31", "0.32", "0.33"}:
            inventory.version = "0.34"
    for gate in session.scalars(select(ReleaseGate).where(ReleaseGate.code.in_(["GATE-ARCH", "GATE-OPS"]))):
        gate.status = "Parcial"
        if gate.code == "GATE-ARCH":
            gate.evidence = "V0.34 extrae el dominio de operación y continuidad del controlador principal y lo registra como módulo web independiente."
            gate.notes = "Pendiente continuar la separación de inventarios, usuarios y reportes antes de aprobar la arquitectura V1."
        else:
            gate.evidence = "V0.34 valida respaldos mediante restauración aislada, integridad SQLite/tablas críticas y trazabilidad de ensayos."
            gate.notes = "La puerta requiere al menos un ensayo aprobado con datos reales, monitoreo externo y despliegue productivo antes de V1."
    if settings.seed_demo:
        for org in session.scalars(select(Organization)).all():
            admin = session.scalar(select(AppUser).where(AppUser.organization_id == org.id, AppUser.role == "Administrador"))
            title = "Continuidad operativa V0.34 disponible"
            existing = session.scalar(select(Notification).where(Notification.organization_id == org.id, Notification.title == title))
            if admin and not existing:
                session.add(Notification(organization_id=org.id, user_id=admin.id, title=title, message="Genera un respaldo y ejecuta un ensayo de restauración aislado desde Operación y seguridad.", link="/operacion", category="Operación", priority="Alta", status="Entregada"))
    session.flush()


def _ensure_v035_defaults(session: Session) -> None:
    """Record domain modularization while preserving all historical data."""
    previous_versions = {
        "0.20", "0.21", "0.22", "0.23", "0.24", "0.25", "0.26", "0.27",
        "0.28", "0.29", "0.30", "0.31", "0.32", "0.33", "0.34",
    }
    for inventory in session.scalars(select(Inventory)):
        if inventory.version in previous_versions:
            inventory.version = "0.35"

    gate = session.scalar(select(ReleaseGate).where(ReleaseGate.code == "GATE-ARCH"))
    if gate:
        gate.status = "Parcial"
        gate.evidence = (
            "V0.35 separa usuarios y membresías, inventarios y fuentes, informes y continuidad "
            "en módulos web con paridad de rutas verificada."
        )
        gate.notes = (
            "La arquitectura sigue en transición: database.py y otros dominios administrativos "
            "continúan concentrados antes de V1."
        )

    finding = session.scalar(select(ConsolidationFinding).where(ConsolidationFinding.code == "TD-001"))
    if finding:
        finding.status = "En curso"
        finding.owner = "Arquitectura"
        finding.target_version = "V0.36"
        finding.evidence = (
            "main.py redujo rutas de usuarios, inventarios, fuentes y reportes; "
            "la propiedad de rutas se valida en /api/arquitectura/resumen."
        )

    if settings.seed_demo:
        for org in session.scalars(select(Organization)).all():
            admin = session.scalar(
                select(AppUser).where(
                    AppUser.organization_id == org.id,
                    AppUser.role == "Administrador",
                )
            )
            title = "Arquitectura por dominios V0.35 disponible"
            existing = session.scalar(
                select(Notification).where(
                    Notification.organization_id == org.id,
                    Notification.title == title,
                )
            )
            if admin and not existing:
                session.add(
                    Notification(
                        organization_id=org.id,
                        user_id=admin.id,
                        title=title,
                        message=(
                            "Usuarios, inventarios, fuentes, reportes y continuidad ya tienen "
                            "módulos web independientes con paridad de rutas."
                        ),
                        link="/consolidacion#arquitectura-dominios",
                        category="Arquitectura",
                        priority="Media",
                        status="Entregada",
                    )
                )
    session.flush()


def _ensure_v036_defaults(session: Session) -> None:
    """Record the second domain extraction wave without changing calculations."""
    previous_versions = {
        "0.20", "0.21", "0.22", "0.23", "0.24", "0.25", "0.26", "0.27",
        "0.28", "0.29", "0.30", "0.31", "0.32", "0.33", "0.34", "0.35",
    }
    for inventory in session.scalars(select(Inventory)):
        if inventory.version in previous_versions:
            inventory.version = "0.36"

    gate = session.scalar(select(ReleaseGate).where(ReleaseGate.code == "GATE-ARCH"))
    if gate:
        gate.status = "Parcial"
        gate.evidence = (
            "V0.36 amplía la arquitectura por dominios: organización y sedes, datos y evidencias, "
            "y revisión y cierre se separan del controlador principal con paridad de rutas verificada."
        )
        gate.notes = (
            "Permanecen por extraer dominios avanzados y dividir database.py antes de aprobar "
            "la arquitectura productiva V1."
        )

    finding = session.scalar(select(ConsolidationFinding).where(ConsolidationFinding.code == "TD-001"))
    if finding:
        finding.status = "En curso"
        finding.owner = "Arquitectura"
        finding.target_version = "V0.45"
        finding.evidence = (
            "Siete dominios web poseen rutas explícitas; main.py se redujo y la propiedad se "
            "valida en /api/arquitectura/resumen."
        )

    if settings.seed_demo:
        for org in session.scalars(select(Organization)).all():
            admin = session.scalar(
                select(AppUser).where(
                    AppUser.organization_id == org.id,
                    AppUser.role == "Administrador",
                )
            )
            title = "Arquitectura ampliada V0.36 disponible"
            existing = session.scalar(
                select(Notification).where(
                    Notification.organization_id == org.id,
                    Notification.title == title,
                )
            )
            if admin and not existing:
                session.add(
                    Notification(
                        organization_id=org.id,
                        user_id=admin.id,
                        title=title,
                        message=(
                            "Organización, sedes, datos, evidencias y revisión ya operan en "
                            "módulos independientes con las mismas rutas y permisos."
                        ),
                        link="/consolidacion#arquitectura-dominios",
                        category="Arquitectura",
                        priority="Media",
                        status="Entregada",
                    )
                )
    session.flush()


def _ensure_v037_defaults(session: Session) -> None:
    """Record persistence modularization without changing historical calculations."""
    previous_versions = {
        "0.20", "0.21", "0.22", "0.23", "0.24", "0.25", "0.26", "0.27",
        "0.28", "0.29", "0.30", "0.31", "0.32", "0.33", "0.34", "0.35", "0.36",
    }
    for inventory in session.scalars(select(Inventory)):
        if inventory.version in previous_versions:
            inventory.version = "0.37"

    gate = session.scalar(select(ReleaseGate).where(ReleaseGate.code == "GATE-ARCH"))
    if gate:
        gate.status = "Parcial"
        gate.evidence = (
            "V0.45 divide los 101 modelos ORM en nueve dominios persistentes, reduce database.py "
            "y agrega repositorios y servicios para organización, inventarios e informes."
        )
        gate.notes = (
            "La compatibilidad pública de app.database se conserva. Antes de V1 deben ampliarse "
            "repositorios y servicios al resto de dominios y validar PostgreSQL administrado."
        )

    finding = session.scalar(select(ConsolidationFinding).where(ConsolidationFinding.code == "TD-001"))
    if finding:
        finding.status = "En curso"
        finding.owner = "Arquitectura"
        finding.target_version = "V0.38"
        finding.evidence = (
            "database.py pasó a ser una fachada compatible; los modelos viven en app/db/models "
            "y la separación se audita en /api/arquitectura/resumen."
        )

    if settings.seed_demo:
        for org in session.scalars(select(Organization)).all():
            admin = session.scalar(
                select(AppUser).where(
                    AppUser.organization_id == org.id,
                    AppUser.role == "Administrador",
                )
            )
            title = "Persistencia por dominios V0.45 disponible"
            existing = session.scalar(
                select(Notification).where(
                    Notification.organization_id == org.id,
                    Notification.title == title,
                )
            )
            if admin and not existing:
                session.add(
                    Notification(
                        organization_id=org.id,
                        user_id=admin.id,
                        title=title,
                        message=(
                            "Los modelos, repositorios y servicios principales ya están separados "
                            "por dominio sin modificar datos ni resultados históricos."
                        ),
                        link="/consolidacion#arquitectura-dominios",
                        category="Arquitectura",
                        priority="Media",
                        status="Entregada",
                    )
                )
    session.flush()



def _ensure_v043_defaults(session: Session) -> None:
    """Reconcile operational readiness capabilities without changing calculations."""
    previous_versions = {
        "0.20", "0.21", "0.22", "0.23", "0.24", "0.25", "0.26", "0.27",
        "0.28", "0.29", "0.30", "0.31", "0.32", "0.33", "0.34", "0.35", "0.36", "0.37",
    }
    for inventory in session.scalars(select(Inventory)):
        if inventory.version in previous_versions:
            inventory.version = "0.43"

    gate = session.scalar(select(ReleaseGate).where(ReleaseGate.code == "GATE-OPS"))
    if gate:
        gate.status = "Parcial"
        gate.evidence = (
            "V0.45 incorpora puerta productiva, métricas Prometheus, incidentes operativos, "
            "almacenamiento externo filesystem/S3 y ensayo de despliegue auditable."
        )
        gate.notes = (
            "La aprobación estricta exige PostgreSQL, almacenamiento externo, HTTPS, secretos, "
            "métricas protegidas y ensayo de restauración vigente."
        )

    if settings.seed_demo:
        for org in session.scalars(select(Organization)).all():
            admin = session.scalar(select(AppUser).where(
                AppUser.organization_id == org.id,
                AppUser.role == "Administrador",
            ))
            title = "Operación controlada V0.45 disponible"
            existing = session.scalar(select(Notification).where(
                Notification.organization_id == org.id,
                Notification.title == title,
            ))
            if admin and not existing:
                session.add(Notification(
                    organization_id=org.id,
                    user_id=admin.id,
                    title=title,
                    message=(
                        "La puerta productiva identifica bloqueos reales, registra incidentes y "
                        "permite ensayar el despliegue sin aprobar dependencias no conectadas."
                    ),
                    link="/operacion#despliegue-controlado",
                    category="Operación",
                    priority="Alta",
                    status="Entregada",
                ))
    session.flush()


def _ensure_v044_defaults(session: Session) -> None:
    """Prepare the certified demonstration environment without affecting production data."""
    previous_versions = {
        "0.20", "0.21", "0.22", "0.23", "0.24", "0.25", "0.26", "0.27",
        "0.28", "0.29", "0.30", "0.31", "0.32", "0.33", "0.34", "0.35", "0.36",
        "0.37", "0.38", "0.39", "0.40", "0.41", "0.42", "0.43",
    }
    for inventory in session.scalars(select(Inventory)):
        if inventory.version in previous_versions:
            inventory.version = "0.45"
    if settings.seed_demo:
        from .demo_environment import ensure_demo_environment
        ensure_demo_environment(session)
    session.flush()



def _ensure_v045_defaults(session: Session) -> None:
    """Activate the product-intelligence layer without inventing production data."""
    previous_versions = {
        "0.20", "0.21", "0.22", "0.23", "0.24", "0.25", "0.26", "0.27",
        "0.28", "0.29", "0.30", "0.31", "0.32", "0.33", "0.34", "0.35", "0.36",
        "0.37", "0.38", "0.39", "0.40", "0.41", "0.42", "0.43", "0.44", "0.45",
    }
    for inventory in session.scalars(select(Inventory)):
        if inventory.version in previous_versions:
            inventory.version = "0.45"

    # Every organization gets an empty profile container; content remains user-provided.
    for organization in session.scalars(select(Organization)):
        profile = session.scalar(select(OrganizationCarbonProfile).where(
            OrganizationCarbonProfile.organization_id == organization.id
        ))
        if not profile:
            session.add(OrganizationCarbonProfile(
                organization_id=organization.id,
                company_size=("Micro" if organization.employees <= 10 else "Pequeña" if organization.employees <= 50 else "Mediana" if organization.employees <= 200 else "Grande"),
                sector_subsector=organization.sector,
                countries_count=1,
                countries_json=json.dumps([organization.country or "Colombia"], ensure_ascii=False),
                status="En construcción",
                source="Migración V0.45",
                updated_by="sistema-v045",
            ))

    # Align commercial names with the three levels of environmental service.
    plan_updates = {
        "ESENCIAL": ("Huella Esencial", "Diagnóstico, alcances 1 y 2, carga anual, cálculo asistido e informe ejecutivo."),
        "EMPRESARIAL": ("Gestión de Carbono", "Seguimiento periódico, alcance 3 priorizado, calidad, cierre, indicadores y reducción."),
        "CORPORATIVO": ("Gestión Avanzada y Verificación", "Alcance 3 profundo, proveedores, incertidumbre, escenarios y preparación para verificación."),
    }
    for code, (name, description) in plan_updates.items():
        plan = session.scalar(select(ServicePlan).where(ServicePlan.code == code))
        if plan:
            plan.name = name
            plan.description = description

    if settings.seed_demo:
        from .services.product_intelligence import ensure_demo_product_intelligence
        ensure_demo_product_intelligence(session)
    session.flush()

def init_db() -> None:
    Base.metadata.create_all(ENGINE)
    with SessionLocal() as session:
        existing = session.scalar(select(Organization).limit(1))
        if existing:
            _ensure_v020_defaults(session)
            _ensure_v021_defaults(session)
            _ensure_v022_defaults(session)
            _ensure_v023_defaults(session)
            _ensure_v024_defaults(session)
            _ensure_v025_defaults(session)
            _ensure_v026_defaults(session)
            _ensure_v027_defaults(session)
            _ensure_v028_defaults(session)
            _ensure_v030_defaults(session)
            _ensure_v031_defaults(session)
            _ensure_v032_defaults(session)
            _ensure_v033_defaults(session)
            _ensure_v034_defaults(session)
            _ensure_v035_defaults(session)
            _ensure_v036_defaults(session)
            _ensure_v037_defaults(session)
            _ensure_v043_defaults(session)
            _ensure_v044_defaults(session)
            _ensure_v045_defaults(session)
            session.commit()
            return

        methodology = _seed_methodology(session)
        _seed_sector_templates(session)
        versions: dict[str, EmissionFactorVersion] = methodology["versions"]  # type: ignore[assignment]

        if not settings.seed_demo:
            if settings.bootstrap_admin_email and settings.bootstrap_admin_password:
                org = Organization(
                    name=settings.bootstrap_organization, trade_name=settings.bootstrap_organization,
                    tax_id="PENDIENTE", sector="Por configurar", country="Colombia", city="Por configurar",
                    contact_name="Administrador", contact_email=settings.bootstrap_admin_email, status="Activa",
                )
                session.add(org)
                session.flush()
                session.add(AppUser(
                    organization_id=org.id, email=settings.bootstrap_admin_email, name="Administrador inicial",
                    role="Administrador", password_hash=hash_password(settings.bootstrap_admin_password), active=True,
                ))
            _ensure_v020_defaults(session)
            _ensure_v021_defaults(session)
            _ensure_v022_defaults(session)
            _ensure_v023_defaults(session)
            _ensure_v024_defaults(session)
            _ensure_v025_defaults(session)
            _ensure_v026_defaults(session)
            _ensure_v027_defaults(session)
            _ensure_v028_defaults(session)
            _ensure_v030_defaults(session)
            _ensure_v031_defaults(session)
            _ensure_v032_defaults(session)
            _ensure_v033_defaults(session)
            _ensure_v034_defaults(session)
            _ensure_v035_defaults(session)
            _ensure_v036_defaults(session)
            _ensure_v037_defaults(session)
            _ensure_v043_defaults(session)
            _ensure_v044_defaults(session)
            _ensure_v045_defaults(session)
            session.commit()
            return

        org = Organization(
            name="Industrias Andinas Demo S.A.S.", trade_name="Industrias Andinas", tax_id="901.555.101-8",
            sector="Manufactura", ciiu_code="C2029", country="Colombia", department="Antioquia", city="Medellín",
            employees=186, annual_revenue=18_500_000_000, contact_name="Ana Martínez", contact_email="ambiental@industriasandinas.demo",
        )
        session.add(org)
        session.flush()

        demo_password = hash_password("Demo2026!")
        session.add_all([
            AppUser(organization_id=org.id, email="admin@calculatuhuella.local", name="Laura Méndez", role="Administrador", password_hash=demo_password),
            AppUser(organization_id=org.id, email="consultor@calculatuhuella.local", name="Carlos Uribe", role="Consultor", password_hash=demo_password),
            AppUser(organization_id=org.id, email="cliente@calculatuhuella.local", name="Ana Martínez", role="Cliente", password_hash=demo_password),
            AppUser(organization_id=org.id, email="revisor@calculatuhuella.local", name="María Fernández", role="Revisor", password_hash=demo_password),
            AppUser(organization_id=org.id, email="verificador@calculatuhuella.local", name="Andrés Salazar", role="Verificador", password_hash=demo_password),
        ])

        session.flush()
        demo_users = {user.role: user for user in session.scalars(select(AppUser).where(AppUser.organization_id == org.id))}
        for demo_user in demo_users.values():
            session.add(NotificationPreference(user_id=demo_user.id, in_app_enabled=True, email_enabled=True, digest_frequency="Inmediato"))
        session.add_all([
            Notification(organization_id=org.id, user_id=demo_users["Consultor"].id, title="Divulgación climática disponible", message="La V0.20 incorporó comparación de escenarios, matriz de divulgación y paquete ejecutivo para comité directivo.", link="/divulgacion-climatica", category="Producto", priority="Normal", status="Entregada"),
            Notification(organization_id=org.id, user_id=demo_users["Revisor"].id, title="Revisión pendiente", message="El inventario corporativo 2025 contiene observaciones abiertas que requieren seguimiento.", link="/control", category="Revisión", priority="Alta", status="Entregada"),
            Notification(organization_id=org.id, user_id=demo_users["Administrador"].id, title="Configuración productiva", message="Revisa almacenamiento, correo y migraciones desde Administración de plataforma.", link="/administracion-plataforma", category="Operación", priority="Normal", status="Entregada"),
        ])
        session.add_all([
            PlatformSetting(organization_id=org.id, key="brand_descriptor", value="Plataforma profesional de huella de carbono", description="Descriptor visible de la marca"),
            PlatformSetting(organization_id=org.id, key="default_methodology", value="GHG Protocol + ISO 14064-1", description="Metodología sugerida para inventarios nuevos"),
            PlatformSetting(organization_id=org.id, key="data_retention_years", value="7", value_type="integer", description="Retención documental recomendada"),
        ])

        facilities = [
            Facility(organization_id=org.id, name="Planta Medellín", facility_type="Planta de producción", city="Medellín", address="Zona industrial Guayabal", employees=118),
            Facility(organization_id=org.id, name="Bodega Rionegro", facility_type="Centro de distribución", city="Rionegro", address="Zona Franca", employees=42),
            Facility(organization_id=org.id, name="Oficina administrativa", facility_type="Oficina", city="Medellín", address="El Poblado", employees=26),
        ]
        session.add_all(facilities)
        session.flush()

        inv = Inventory(
            organization_id=org.id, name="Inventario corporativo 2025", start_date=date(2025, 1, 1), end_date=date(2025, 12, 31),
            objective="Establecer la línea base corporativa, responder requisitos de clientes y priorizar reducciones.", base_year=2025,
            methodology="GHG Protocol + ISO 14064-1", methodology_version="GHG Protocol Corporate Standard · ISO 14064-1:2018",
            gwp_version="IPCC AR6 · 100 años", consolidation_approach="Control operacional", materiality_threshold=5,
            status="Activo", progress=0, current_stage="Cálculo", notes="Inventario demostrativo con motor matemático, control profesional, cadena de valor, escenarios y verificación y operación productiva, migraciones, almacenamiento, notificaciones, automatizaciones e integraciones, gobierno metodológico, cumplimiento y operación SaaS, flujo comercial y operación contractual y éxito del cliente, inteligencia de impacto y riesgos climáticos V0.20.", version="0.20",
        )
        session.add(inv)
        session.flush()
        for facility in facilities:
            session.add(InventoryFacility(inventory_id=inv.id, facility_id=facility.id, included=True, inclusion_percentage=100))

        sources = [
            EmissionSource(inventory_id=inv.id, facility_id=facilities[0].id, name="Electricidad", scope=2, category="Energía adquirida", responsible="Contabilidad", materiality="Alta", data_frequency="Mensual", preferred_unit="kWh", icon="bolt"),
            EmissionSource(inventory_id=inv.id, facility_id=facilities[0].id, name="Diésel", scope=1, category="Combustión fija", responsible="Mantenimiento", materiality="Alta", data_frequency="Mensual", preferred_unit="L", icon="fuel"),
            EmissionSource(inventory_id=inv.id, facility_id=facilities[1].id, name="Vehículos", scope=1, category="Combustión móvil", responsible="Logística", materiality="Alta", data_frequency="Mensual", preferred_unit="L", icon="truck"),
            EmissionSource(inventory_id=inv.id, facility_id=facilities[0].id, name="Refrigerantes", scope=1, category="Emisiones fugitivas", responsible="Mantenimiento", materiality="Media", data_frequency="Anual", preferred_unit="kg", icon="snow"),
            EmissionSource(inventory_id=inv.id, facility_id=facilities[0].id, name="Residuos", scope=3, category="Residuos operacionales", responsible="Gestión ambiental", materiality="Media", data_frequency="Mensual", preferred_unit="t", icon="waste"),
            EmissionSource(inventory_id=inv.id, facility_id=facilities[1].id, name="Transporte contratado", scope=3, category="Transporte y distribución", responsible="Logística", materiality="Alta", data_frequency="Mensual", preferred_unit="t·km", icon="route"),
            EmissionSource(inventory_id=inv.id, facility_id=None, name="Bienes y servicios adquiridos", scope=3, category="Datos específicos de proveedores", responsible="Compras sostenibles", materiality="Alta", data_frequency="Anual", preferred_unit="tCO₂e", icon="suppliers"),
        ]
        session.add_all(sources)
        session.flush()

        assignment_map = {
            0: ["Electricidad de red Colombia · demo"],
            1: ["Diésel combustión fija · CO2 demo", "Diésel combustión fija · CH4 demo", "Diésel combustión fija · N2O demo"],
            2: ["Gasolina vehículos · CO2e demo"],
            3: ["Refrigerante · demo"],
            4: ["Residuos gestionados · demo"],
            5: ["Transporte de carga · demo"],
        }
        for index, names in assignment_map.items():
            for factor_name in names:
                session.add(SourceFactorAssignment(source_id=sources[index].id, factor_version_id=versions[factor_name].id, active=True, assigned_by="sistema", notes="Asignación demostrativa V0.4"))

        demo_dir = UPLOAD_DIR / f"org_{org.id}" / f"inventory_{inv.id}"
        demo_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = demo_dir / "facturas_energia_2025.pdf"
        write_simple_pdf(pdf_path, "Calcula tu Huella - soporte demostrativo de electricidad 2025")
        pdf_bytes = pdf_path.read_bytes()
        electricity_doc = EvidenceDocument(
            inventory_id=inv.id, source_id=sources[0].id, name="Facturas_energia_2025.pdf",
            stored_name=str(pdf_path.relative_to(INSTANCE_DIR)), document_type="Factura", source_name="Electricidad",
            period_label="Enero–diciembre 2025", status="Aprobado", uploaded_by="Ana Martínez",
            file_size=len(pdf_bytes), sha256=hashlib.sha256(pdf_bytes).hexdigest(), notes="Soporte demostrativo descargable.",
        )
        session.add(electricity_doc)

        xlsx_path = demo_dir / "consolidado_diesel_2025.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.title = "Consolidado"
        ws.append(["Mes", "Litros"])
        diesel_values = [1210, 1185, 1250, 1190, 1280, 1310, 1275, 1235, 1295, 1325, 1260, 1305]
        for month, value in enumerate(diesel_values, 1):
            ws.append([date(2025, month, 1), value])
        wb.save(xlsx_path)
        xlsx_bytes = xlsx_path.read_bytes()
        diesel_doc = EvidenceDocument(
            inventory_id=inv.id, source_id=sources[1].id, name="Consolidado_diesel_2025.xlsx",
            stored_name=str(xlsx_path.relative_to(INSTANCE_DIR)), document_type="Registro operativo", source_name="Diésel",
            period_label="2025", status="En revisión", uploaded_by="Ana Martínez", file_size=len(xlsx_bytes),
            sha256=hashlib.sha256(xlsx_bytes).hexdigest(),
        )
        session.add(diesel_doc)
        session.flush()

        electricity_values = [18450, 17980, 18820, 18140, 19010, 19480, 19220, 18790, 19610, 19930, 19350, 20120]
        for month, value in enumerate(electricity_values, 1):
            session.add(ActivityData(source_id=sources[0].id, evidence_id=electricity_doc.id, period_start=date(2025, month, 1), period_end=date(2025, month, 28), value=value, unit="kWh", data_origin="Factura", quality_level="A", status="Aprobado", notes="Consumo facturado mensual.", created_by="cliente@calculatuhuella.local"))
        for month, value in enumerate(diesel_values, 1):
            session.add(ActivityData(source_id=sources[1].id, evidence_id=diesel_doc.id, period_start=date(2025, month, 1), period_end=date(2025, month, 28), value=value, unit="L", data_origin="Registro operativo", quality_level="B", status="En revisión", notes="Consolidado de abastecimiento.", created_by="cliente@calculatuhuella.local"))
        for month, value in enumerate([780, 760, 810, 795, 820, 835, 800, 790, 845, 830], 1):
            session.add(ActivityData(source_id=sources[2].id, period_start=date(2025, month, 1), period_end=date(2025, month, 28), value=value, unit="L", data_origin="Registro operativo", quality_level="B", status="Cargado", created_by="cliente@calculatuhuella.local"))
        session.add(ActivityData(source_id=sources[3].id, period_start=date(2025, 1, 1), period_end=date(2025, 12, 31), value=34.5, unit="kg", data_origin="Registro operativo", quality_level="B", status="En revisión", created_by="cliente@calculatuhuella.local"))
        for month, value in enumerate([18.2, 17.6, 19.1, 18.8, 20.4, 19.7], 1):
            session.add(ActivityData(source_id=sources[4].id, period_start=date(2025, month, 1), period_end=date(2025, month, 28), value=value, unit="t", data_origin="Certificado", quality_level="B", status="Cargado", created_by="cliente@calculatuhuella.local"))
        for month, value in enumerate([12800, 13450, 13100], 1):
            session.add(ActivityData(source_id=sources[5].id, period_start=date(2025, month, 1), period_end=date(2025, month, 28), value=value, unit="t·km", data_origin="Estimación", quality_level="C", is_estimated=True, status="Provisional", notes="Distancia estimada a partir de ruta estándar.", created_by="cliente@calculatuhuella.local"))

        # Indicadores operativos reales para intensidad y comparación.
        production_values = [980, 1010, 1040, 1025, 1080, 1115, 1090, 1065, 1120, 1140, 1105, 1190]
        for month, value in enumerate(production_values, 1):
            session.add(ActivityIndicator(
                inventory_id=inv.id, facility_id=facilities[0].id,
                period_start=date(2025, month, 1), period_end=date(2025, month, 28),
                indicator_type="Producción", value=value, unit="t",
                source_name="Registro de producción", status="Aprobado",
                created_by="cliente@calculatuhuella.local",
            ))
        session.add(ActivityIndicator(
            inventory_id=inv.id, period_start=date(2025, 1, 1), period_end=date(2025, 12, 31),
            indicator_type="Empleados", value=186, unit="personas", source_name="Nómina",
            status="Aprobado", created_by="cliente@calculatuhuella.local",
        ))
        session.add(ActivityIndicator(
            inventory_id=inv.id, period_start=date(2025, 1, 1), period_end=date(2025, 12, 31),
            indicator_type="Ingresos", value=18_500_000_000, unit="COP", source_name="Estados financieros",
            status="En revisión", created_by="cliente@calculatuhuella.local",
        ))

        session.add_all([
            ReductionAction(
                inventory_id=inv.id, source_id=sources[1].id, title="Optimización de combustión de la caldera",
                description="Ajustar relación aire-combustible, mantenimiento de quemadores y control de eficiencia térmica.",
                baseline_emissions=0, expected_reduction=8.5, investment_cost=28_000_000, annual_savings=42_000_000,
                priority="Alta", responsible="Mantenimiento", target_date=date(2026, 6, 30),
                status="En evaluación", progress_percent=55, created_by="consultor@calculatuhuella.local",
            ),
            ReductionAction(
                inventory_id=inv.id, source_id=sources[0].id, title="Autogeneración solar fotovoltaica",
                description="Instalar un sistema solar para cubrir parte del consumo de la planta Medellín.",
                baseline_emissions=0, expected_reduction=31.0, investment_cost=310_000_000, annual_savings=76_000_000,
                priority="Alta", responsible="Gerencia de operaciones", target_date=date(2027, 3, 31),
                status="Diseño", progress_percent=35, created_by="consultor@calculatuhuella.local",
            ),
            ReductionAction(
                inventory_id=inv.id, source_id=sources[3].id, title="Programa de control de fugas de refrigerantes",
                description="Inventario de equipos, pruebas periódicas de hermeticidad y sustitución progresiva de gases.",
                baseline_emissions=0, expected_reduction=21.5, investment_cost=18_000_000, annual_savings=8_000_000,
                priority="Media", responsible="Mantenimiento", target_date=date(2026, 9, 30),
                status="Identificada", progress_percent=15, created_by="consultor@calculatuhuella.local",
            ),
        ])

        session.add(EmissionTarget(
            inventory_id=inv.id, name="Reducir emisiones absolutas al 2030", metric_type="Absoluta",
            baseline_year=2025, target_year=2030, baseline_value=0, target_value=0, current_value=0,
            unit="tCO₂e", status="Activa", notes="Meta demostrativa: reducción del 20 % frente a la línea base 2025.",
            created_by="consultor@calculatuhuella.local",
        ))

        # Inventario histórico resumido para validar comparación interanual.
        prior = Inventory(
            organization_id=org.id, name="Inventario corporativo 2024", start_date=date(2024, 1, 1), end_date=date(2024, 12, 31),
            objective="Inventario histórico para comparación", base_year=2024, methodology="GHG Protocol + ISO 14064-1",
            methodology_version="GHG Protocol Corporate Standard · ISO 14064-1:2018",
            gwp_version="IPCC AR6 · 100 años", consolidation_approach="Control operacional", materiality_threshold=5,
            status="Cerrado", progress=100, current_stage="Cerrado", notes="Inventario histórico demostrativo.",
            version="1.0", locked=True, closed_by="sistema", closed_at=datetime.now(UTC),
        )
        session.add(prior)
        session.flush()
        for facility in facilities:
            session.add(InventoryFacility(inventory_id=prior.id, facility_id=facility.id, included=True, inclusion_percentage=100))
        prior_sources = [
            EmissionSource(inventory_id=prior.id, facility_id=facilities[0].id, name="Electricidad", scope=2, category="Energía adquirida", progress=100, status="Completado", emissions=52.8),
            EmissionSource(inventory_id=prior.id, facility_id=facilities[0].id, name="Diésel", scope=1, category="Combustión fija", progress=100, status="Completado", emissions=44.9),
            EmissionSource(inventory_id=prior.id, facility_id=facilities[1].id, name="Vehículos", scope=1, category="Combustión móvil", progress=100, status="Completado", emissions=23.6),
            EmissionSource(inventory_id=prior.id, facility_id=facilities[0].id, name="Refrigerantes", scope=1, category="Emisiones fugitivas", progress=100, status="Completado", emissions=79.4),
            EmissionSource(inventory_id=prior.id, facility_id=facilities[0].id, name="Residuos", scope=3, category="Residuos operacionales", progress=100, status="Completado", emissions=61.2),
            EmissionSource(inventory_id=prior.id, facility_id=facilities[1].id, name="Transporte contratado", scope=3, category="Transporte y distribución", progress=100, status="Completado", emissions=15.7),
        ]
        session.add_all(prior_sources)
        session.add_all([
            ActivityIndicator(inventory_id=prior.id, period_start=date(2024, 1, 1), period_end=date(2024, 12, 31), indicator_type="Producción", value=11_840, unit="t", source_name="Registro histórico", status="Aprobado", created_by="sistema"),
            ActivityIndicator(inventory_id=prior.id, period_start=date(2024, 1, 1), period_end=date(2024, 12, 31), indicator_type="Empleados", value=178, unit="personas", source_name="Nómina", status="Aprobado", created_by="sistema"),
            ActivityIndicator(inventory_id=prior.id, period_start=date(2024, 1, 1), period_end=date(2024, 12, 31), indicator_type="Ingresos", value=16_900_000_000, unit="COP", source_name="Estados financieros", status="Aprobado", created_by="sistema"),
        ])

        session.add_all([
            DataRequest(inventory_id=inv.id, source_id=sources[1].id, title="Validar consolidado de diésel", source_name="Diésel", requested_to="Mantenimiento", due_date=date(2026, 8, 15), status="En revisión", instructions="Confirmar consumos mensuales y adjuntar reporte de abastecimiento."),
            DataRequest(inventory_id=inv.id, source_id=sources[5].id, title="Completar transporte contratado", source_name="Transporte contratado", requested_to="Logística", due_date=date(2026, 8, 20), status="Pendiente", instructions="Cargar toneladas, rutas y kilómetros recorridos por proveedor."),
            DataRequest(inventory_id=inv.id, source_id=sources[3].id, title="Subir soporte de refrigerantes", source_name="Refrigerantes", requested_to="Mantenimiento", due_date=date(2026, 8, 22), status="Pendiente", instructions="Adjuntar mantenimientos, recargas y recuperación de gas."),
        ])
        session.add_all([
            ReviewObservation(
                inventory_id=inv.id, source_id=sources[5].id, entity_type="Fuente", entity_label="Transporte contratado",
                title="Completar cobertura anual de transporte contratado",
                description="Solo existen tres periodos y los datos fueron estimados. Completar la actividad anual y adjuntar soporte del proveedor.",
                severity="Mayor", status="Abierta", assigned_to="Logística", due_date=date(2026, 8, 20),
                created_by="revisor@calculatuhuella.local",
            ),
            ReviewObservation(
                inventory_id=inv.id, source_id=sources[3].id, entity_type="Fuente", entity_label="Refrigerantes",
                title="Adjuntar soporte de recargas y recuperación",
                description="El dato anual existe, pero no está relacionado con una evidencia documental.",
                severity="Menor", status="En corrección", assigned_to="Mantenimiento", due_date=date(2026, 8, 22),
                created_by="revisor@calculatuhuella.local", response="Se solicitó el certificado al proveedor de mantenimiento.",
                responded_by="cliente@calculatuhuella.local", responded_at=datetime.now(UTC),
            ),
            ReviewObservation(
                inventory_id=inv.id, source_id=sources[0].id, entity_type="Fuente", entity_label="Electricidad",
                title="Verificar correspondencia factura-periodo",
                description="Validación de muestra documental sobre tres meses del periodo.",
                severity="Informativa", status="Cerrada", assigned_to="Contabilidad",
                created_by="revisor@calculatuhuella.local", response="Se verificaron enero, junio y diciembre.",
                responded_by="cliente@calculatuhuella.local", responded_at=datetime.now(UTC),
                resolution="La muestra coincide con los registros cargados.", resolved_by="revisor@calculatuhuella.local",
                resolved_at=datetime.now(UTC), closed_by="revisor@calculatuhuella.local", closed_at=datetime.now(UTC),
            ),
        ])

        suppliers = [
            Supplier(organization_id=org.id, name="Acero Circular S.A.S.", tax_id="900.111.222-3", sector="Metalmecánico", contact_name="Diana Gómez", contact_email="sostenibilidad@acerocircular.demo", annual_spend_cop=2_450_000_000, strategic=True, risk_level="Alto"),
            Supplier(organization_id=org.id, name="Empaques del Valle S.A.S.", tax_id="901.222.333-4", sector="Empaques", contact_name="Felipe Ríos", contact_email="ambiental@empaquesvalle.demo", annual_spend_cop=980_000_000, strategic=True, risk_level="Medio"),
            Supplier(organization_id=org.id, name="Químicos Andinos Ltda.", tax_id="800.333.444-5", sector="Químicos", contact_name="Laura Peña", contact_email="calidad@quimicosandinos.demo", annual_spend_cop=1_720_000_000, strategic=True, risk_level="Alto"),
            Supplier(organization_id=org.id, name="Servicios Integrales Norte", tax_id="901.444.555-6", sector="Servicios", contact_name="Mateo Díaz", contact_email="operaciones@serviciosnorte.demo", annual_spend_cop=310_000_000, strategic=False, risk_level="Bajo"),
        ]
        session.add_all(suppliers)
        session.flush()
        campaign = SupplierCampaign(
            inventory_id=inv.id, name="Compras estratégicas 2025", category="Bienes y servicios adquiridos",
            due_date=date(2026, 9, 30), status="En curso", methodology="GHG Protocol Scope 3 · categoría 1",
            description="Campaña demostrativa para solicitar factores y huellas específicas a proveedores prioritarios.",
            created_by="consultor@calculatuhuella.local",
        )
        session.add(campaign)
        session.flush()
        supplier_requests = [
            SupplierDataRequest(campaign_id=campaign.id, supplier_id=suppliers[0].id, product_service="Acero laminado", quantity=420, unit="t", spend_cop=2_450_000_000, status="Respondida", due_date=date(2026, 9, 15), access_token="demo-acero-2025", token_expires_at=datetime(2026, 12, 31, tzinfo=UTC), sent_at=datetime.now(UTC), responded_at=datetime.now(UTC)),
            SupplierDataRequest(campaign_id=campaign.id, supplier_id=suppliers[1].id, product_service="Empaques de cartón", quantity=185000, unit="unidad", spend_cop=980_000_000, status="Respondida", due_date=date(2026, 9, 20), access_token="demo-empaques-2025", token_expires_at=datetime(2026, 12, 31, tzinfo=UTC), sent_at=datetime.now(UTC), responded_at=datetime.now(UTC)),
            SupplierDataRequest(campaign_id=campaign.id, supplier_id=suppliers[2].id, product_service="Precursores químicos", quantity=96, unit="t", spend_cop=1_720_000_000, status="Enviada", due_date=date(2026, 9, 25), access_token="demo-quimicos-2025", token_expires_at=datetime(2026, 12, 31, tzinfo=UTC), sent_at=datetime.now(UTC)),
            SupplierDataRequest(campaign_id=campaign.id, supplier_id=suppliers[3].id, product_service="Servicios de mantenimiento", quantity=1, unit="servicio anual", spend_cop=310_000_000, status="Pendiente", due_date=date(2026, 9, 30), access_token="demo-servicios-2025", token_expires_at=datetime(2026, 12, 31, tzinfo=UTC)),
        ]
        session.add_all(supplier_requests)
        session.flush()
        session.add_all([
            SupplierResponse(request_id=supplier_requests[0].id, method="Factor por unidad", activity_value=420, activity_unit="t", emission_factor=710, factor_unit="kg CO2e/t", calculated_emissions_tco2e=298.2, methodology="EPD del producto · cradle-to-gate", boundary="Materias primas, energía y producción hasta puerta de planta", verified=True, quality_level="A", review_status="Aprobado", reviewer_comments="Factor específico y declaración verificada.", reviewed_by="revisor@calculatuhuella.local", reviewed_at=datetime.now(UTC)),
            SupplierResponse(request_id=supplier_requests[1].id, method="Huella total suministrada", activity_value=185000, activity_unit="unidad", reported_emissions_tco2e=42.6, calculated_emissions_tco2e=42.6, methodology="Inventario corporativo asignado por volumen", boundary="Producción y transporte primario", verified=False, quality_level="B", review_status="Aprobado", reviewer_comments="Aceptado con recomendación de mejorar la regla de asignación.", reviewed_by="revisor@calculatuhuella.local", reviewed_at=datetime.now(UTC)),
        ])

        session.flush()
        refresh_progress(session, inv)
        add_audit(session, org.id, "sistema", "CREAR", "Organización", org.name, "Carga inicial de datos demostrativos V0.4")
        add_audit(session, org.id, "sistema", "CONFIGURAR", "Motor de cálculo", "Biblioteca V0.4", "Unidades, GWP, factores y asignaciones iniciales")
        add_audit(session, org.id, "sistema", "CONFIGURAR", "Control profesional", "Flujo V0.5", "Observaciones, decisiones, aprobación, cierre e inmutabilidad")
        session.commit()

        # Import local para evitar dependencia circular durante la definición de modelos.
        from .calculations import recalculate_inventory

        inventory = session.scalar(select(Inventory).where(Inventory.id == inv.id))
        recalculate_inventory(session, inventory)
        session.flush()
        total_emissions = sum(source.emissions for source in inventory.sources if source.included)
        for action in inventory.reduction_actions:
            action.baseline_emissions = action.source.emissions if action.source else total_emissions
        action_profiles = {
            "Optimización de combustión de la caldera": (8, 2026, "Alta", "Bajo"),
            "Autogeneración solar fotovoltaica": (20, 2027, "Media", "Medio"),
            "Programa de control de fugas de refrigerantes": (5, 2026, "Alta", "Bajo"),
        }
        for action in inventory.reduction_actions:
            life, year, feasibility, risk = action_profiles.get(action.title, (5, 2026, "Media", "Medio"))
            action.useful_life_years = life
            action.implementation_year = year
            action.feasibility = feasibility
            action.risk_level = risk
        for target in inventory.targets:
            target.baseline_value = total_emissions
            target.target_value = total_emissions * 0.80
            target.current_value = total_emissions
        scenario = ReductionScenario(
            inventory_id=inventory.id,
            name="Escenario priorizado 2030",
            description="Portafolio demostrativo de medidas priorizadas por costo, reducción y viabilidad.",
            start_year=2026,
            target_year=2030,
            discount_rate=10.0,
            status="En evaluación",
            created_by="consultor@calculatuhuella.local",
        )
        session.add(scenario)
        session.flush()
        for action in inventory.reduction_actions:
            session.add(ReductionScenarioAction(
                scenario_id=scenario.id,
                action_id=action.id,
                included=True,
                implementation_year=action.implementation_year,
                adoption_percent=100.0,
            ))
        session.add(VerificationFinding(
            inventory_id=inventory.id,
            source_id=sources[5].id,
            title="Trazabilidad incompleta del transporte contratado",
            description="La muestra disponible no cubre el periodo completo y utiliza estimaciones sin soporte primario del proveedor.",
            finding_type="Solicitud de información",
            severity="Mayor",
            status="Abierto",
            verifier_email="verificador@calculatuhuella.local",
        ))
        add_audit(session, org.id, "sistema", "CONFIGURAR", "Gestión climática", "Módulos V0.20", "Escenarios comparados, divulgación climática y paquete para comité directivo")
        _ensure_v020_defaults(session)
        _ensure_v021_defaults(session)
        _ensure_v022_defaults(session)
        _ensure_v023_defaults(session)
        _ensure_v024_defaults(session)
        _ensure_v025_defaults(session)
        _ensure_v026_defaults(session)
        _ensure_v027_defaults(session)
        _ensure_v028_defaults(session)
        _ensure_v030_defaults(session)
        _ensure_v031_defaults(session)
        _ensure_v032_defaults(session)
        _ensure_v033_defaults(session)
        _ensure_v034_defaults(session)
        _ensure_v035_defaults(session)
        _ensure_v036_defaults(session)
        _ensure_v037_defaults(session)
        _ensure_v043_defaults(session)
        _ensure_v044_defaults(session)
        _ensure_v045_defaults(session)
        session.commit()
