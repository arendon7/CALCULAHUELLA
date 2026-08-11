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
from .security import hash_password as secure_hash_password
from .audit import add_audit, audit_event_digest, backfill_audit_chain

def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session


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


SUPPLIER_MANAGED_CATEGORY = "Datos específicos de proveedores"


def refresh_progress(session: Session, inventory: Inventory) -> None:
    # ActivityData puede insertarse por source_id mientras activity_records ya está cargada.
    # Consultar la tabla después del flush evita persistir un progreso rezagado un periodo.
    session.flush()
    source_ids = [source.id for source in inventory.sources if source.id is not None]
    periods_by_source: dict[int, set[tuple[int, int]]] = {source_id: set() for source_id in source_ids}
    if source_ids:
        rows = session.execute(
            select(ActivityData.source_id, ActivityData.period_start).where(ActivityData.source_id.in_(source_ids))
        ).all()
        for source_id, period_start in rows:
            periods_by_source.setdefault(int(source_id), set()).add((period_start.year, period_start.month))

    for source in inventory.sources:
        if source.category == SUPPLIER_MANAGED_CATEGORY:
            # Su progreso pertenece a sync_supplier_source(), basado en respuestas aprobadas.
            continue
        expected = source_expected_periods(source)
        count = len(periods_by_source.get(source.id, set()))
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


from .seed_defaults import (
    _ensure_v012_defaults,
    _ensure_v013_defaults,
    _ensure_v014_defaults,
    _ensure_v015_defaults,
    _ensure_v016_defaults,
    _ensure_v017_defaults,
    _ensure_v018_defaults,
    _ensure_v019_defaults,
    _ensure_v020_defaults,
    _ensure_v021_defaults,
    _ensure_v022_defaults,
    _ensure_v023_defaults,
    _ensure_v024_defaults,
    _ensure_v025_defaults,
    _ensure_v026_defaults,
    _ensure_v027_defaults,
    _ensure_v028_defaults,
    _ensure_v030_defaults,
    _ensure_v031_defaults,
    _ensure_v032_defaults,
    _ensure_v033_defaults,
    _ensure_v034_defaults,
    _ensure_v035_defaults,
    _ensure_v036_defaults,
    _ensure_v037_defaults,
    _ensure_v043_defaults,
    _ensure_v044_defaults,
    _ensure_v045_defaults,
    _ensure_v050_defaults,
    _ensure_v100_final_defaults,
)


def init_db() -> None:
    """Initialize persistence through the dedicated bootstrap module.

    Kept here as a compatibility facade because application modules and external
    callers historically import ``init_db`` from ``app.database``.
    """
    from .seed import init_db as bootstrap_init_db

    bootstrap_init_db()
