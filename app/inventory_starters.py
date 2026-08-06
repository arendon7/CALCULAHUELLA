from __future__ import annotations

"""Starter packs for the first inventory.

The catalog only creates operational source records. It does not assign emission
factors or calculate emissions, preserving methodological review and traceability.
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from .database import EmissionSource, Inventory, add_audit


@dataclass(frozen=True)
class StarterSource:
    name: str
    scope: int
    category: str
    preferred_unit: str
    materiality: str = "Media"
    data_frequency: str = "Mensual"
    icon: str = "activity"
    facility_scoped: bool = True
    evidence_hint: str = "Registro operativo o soporte equivalente"


@dataclass(frozen=True)
class StarterPack:
    code: str
    name: str
    summary: str
    recommended_for: str
    sources: tuple[StarterSource, ...]


_PACKS: tuple[StarterPack, ...] = (
    StarterPack(
        code="services",
        name="Servicios y oficinas",
        summary="Cubre consumos y actividades habituales de oficinas, consultoría y servicios profesionales.",
        recommended_for="Empresas de servicios, sedes administrativas y equipos de oficina.",
        sources=(
            StarterSource("Electricidad comprada", 2, "Electricidad adquirida", "kWh", "Alta", "Mensual", "bolt", True, "Factura o reporte del comercializador"),
            StarterSource("Combustibles de vehículos propios", 1, "Combustión móvil", "L", "Media", "Mensual", "fuel", False, "Facturas, vales o control de combustible"),
            StarterSource("Fugas de refrigerantes", 1, "Emisiones fugitivas", "kg", "Media", "Anual", "snow", True, "Registro de mantenimiento o recarga"),
            StarterSource("Residuos generados en la operación", 3, "Residuos generados", "kg", "Media", "Mensual", "waste", True, "Certificado del gestor o registro de pesaje"),
            StarterSource("Viajes de negocio", 3, "Viajes de negocio", "km", "Baja", "Trimestral", "truck", False, "Tiquetes, reporte de agencia o kilometraje"),
        ),
    ),
    StarterPack(
        code="productive",
        name="Operación productiva",
        summary="Inicia el mapa de fuentes de una planta, taller, centro logístico o proceso industrial.",
        recommended_for="Manufactura, agroindustria, plantas de proceso y centros operativos.",
        sources=(
            StarterSource("Electricidad comprada", 2, "Electricidad adquirida", "kWh", "Alta", "Mensual", "bolt", True, "Factura o reporte del comercializador"),
            StarterSource("Combustión estacionaria", 1, "Combustión fija", "m³", "Alta", "Mensual", "fuel", True, "Factura de gas o registro de consumo"),
            StarterSource("Diésel en equipos y vehículos", 1, "Combustión móvil", "L", "Alta", "Mensual", "fuel", True, "Facturas o control de abastecimiento"),
            StarterSource("Fugas de refrigerantes", 1, "Emisiones fugitivas", "kg", "Media", "Anual", "snow", True, "Registro de mantenimiento o recarga"),
            StarterSource("Emisiones de proceso", 1, "Procesos industriales", "kg", "Media", "Mensual", "activity", True, "Balance de masa o registro de producción"),
            StarterSource("Residuos de la operación", 3, "Residuos generados", "t", "Alta", "Mensual", "waste", True, "Certificado del gestor o registro de pesaje"),
            StarterSource("Transporte contratado", 3, "Transporte aguas arriba", "t·km", "Media", "Mensual", "truck", False, "Manifiestos, remisiones o reporte del transportador"),
            StarterSource("Materias primas adquiridas", 3, "Bienes y servicios adquiridos", "kg", "Media", "Mensual", "activity", False, "Compras, inventarios o balance de materiales"),
        ),
    ),
    StarterPack(
        code="agro",
        name="Operación agropecuaria",
        summary="Organiza energía, combustibles, fertilización, suelos, ganadería, residuos e insumos con unidades productivas explícitas.",
        recommended_for="Agricultura, ganadería, silvicultura, cultivos permanentes y agroindustria primaria.",
        sources=(
            StarterSource("Electricidad comprada", 2, "Electricidad adquirida", "kWh", "Alta", "Mensual", "bolt", True, "Factura o reporte del comercializador"),
            StarterSource("Combustibles de maquinaria y vehículos", 1, "Combustión móvil", "L", "Alta", "Mensual", "fuel", True, "Facturas, vales o control de abastecimiento"),
            StarterSource("Fertilización nitrogenada y enmiendas", 1, "Emisiones agropecuarias", "kg", "Alta", "Mensual", "activity", True, "Plan de fertilización, compras y registro de aplicación"),
            StarterSource("Manejo de suelos y residuos agrícolas", 1, "Suelos y biomasa", "ha", "Alta", "Trimestral", "activity", True, "Bitácoras de lote, área, práctica y material incorporado"),
            StarterSource("Fermentación entérica y manejo de estiércol", 1, "Ganadería", "cabeza·mes", "Media", "Mensual", "activity", True, "Inventario animal, dieta, sistema productivo y manejo de estiércol"),
            StarterSource("Fugas de refrigerantes", 1, "Emisiones fugitivas", "kg", "Baja", "Anual", "snow", True, "Registro de mantenimiento o recarga"),
            StarterSource("Insumos agropecuarios adquiridos", 3, "Bienes y servicios adquiridos", "kg", "Media", "Mensual", "activity", False, "Compras, inventarios y fichas de producto"),
            StarterSource("Transporte contratado de insumos y producto", 3, "Transporte aguas arriba y abajo", "t·km", "Media", "Mensual", "truck", False, "Remisiones, distancias, carga y reporte del transportador"),
        ),
    ),
    StarterPack(
        code="waste",
        name="Gestión de residuos",
        summary="Organiza las fuentes típicas de recolección, transporte, tratamiento y valorización de residuos.",
        recommended_for="Gestores, plantas de aprovechamiento, compostaje, biogás y servicios de aseo.",
        sources=(
            StarterSource("Electricidad comprada", 2, "Electricidad adquirida", "kWh", "Alta", "Mensual", "bolt", True, "Factura o reporte del comercializador"),
            StarterSource("Diésel de maquinaria y vehículos", 1, "Combustión móvil", "L", "Alta", "Mensual", "fuel", True, "Facturas o control de abastecimiento"),
            StarterSource("Gasolina de equipos menores", 1, "Combustión móvil", "L", "Media", "Mensual", "fuel", True, "Facturas o control de abastecimiento"),
            StarterSource("Fugas de refrigerantes", 1, "Emisiones fugitivas", "kg", "Baja", "Anual", "snow", True, "Registro de mantenimiento o recarga"),
            StarterSource("Tratamiento biológico de residuos", 1, "Tratamiento de residuos", "t", "Alta", "Mensual", "waste", True, "Registro de ingreso y balance de tratamiento"),
            StarterSource("Disposición de rechazos", 3, "Residuos generados", "t", "Alta", "Mensual", "waste", True, "Certificado del gestor o báscula"),
            StarterSource("Transporte contratado de residuos", 3, "Transporte aguas arriba", "t·km", "Media", "Mensual", "truck", False, "Manifiestos, rutas o reporte del transportador"),
            StarterSource("Insumos y materiales adquiridos", 3, "Bienes y servicios adquiridos", "kg", "Media", "Mensual", "activity", False, "Compras, inventarios o balance de materiales"),
        ),
    ),
)


def starter_pack_catalog() -> list[dict[str, Any]]:
    return [
        {
            "code": pack.code,
            "name": pack.name,
            "summary": pack.summary,
            "recommended_for": pack.recommended_for,
            "source_count": len(pack.sources),
            "sources": [
                {
                    "name": source.name,
                    "scope": source.scope,
                    "category": source.category,
                    "preferred_unit": source.preferred_unit,
                    "materiality": source.materiality,
                    "data_frequency": source.data_frequency,
                    "evidence_hint": source.evidence_hint,
                }
                for source in pack.sources
            ],
        }
        for pack in _PACKS
    ]


def get_starter_pack(code: str) -> StarterPack | None:
    normalized = str(code or "").strip().lower()
    return next((pack for pack in _PACKS if pack.code == normalized), None)


def add_starter_sources(
    session: Session,
    inventory: Inventory,
    *,
    pack_code: str,
    responsible: str,
    actor_email: str,
    facility_id: int | None = None,
) -> list[EmissionSource]:
    """Add missing sources from a controlled starter pack.

    Duplicate detection is deliberately name-based inside the inventory. A pack
    can therefore be applied more than once without multiplying sources.
    """
    pack = get_starter_pack(pack_code)
    if not pack:
        return []

    existing_names = {source.name.strip().casefold() for source in inventory.sources}
    owner = responsible.strip() or "Responsable ambiental"
    created: list[EmissionSource] = []
    for spec in pack.sources:
        if spec.name.casefold() in existing_names:
            continue
        source = EmissionSource(
            inventory_id=inventory.id,
            facility_id=facility_id if spec.facility_scoped else None,
            name=spec.name,
            scope=spec.scope,
            category=spec.category,
            responsible=owner,
            materiality=spec.materiality,
            data_frequency=spec.data_frequency,
            preferred_unit=spec.preferred_unit,
            progress=0,
            status="Pendiente",
            emissions=0,
            icon=spec.icon,
        )
        session.add(source)
        created.append(source)
        existing_names.add(spec.name.casefold())

    if created:
        inventory.current_stage = "Fuentes"
        inventory.progress = max(inventory.progress, 28)
        add_audit(
            session,
            inventory.organization_id,
            actor_email,
            "CREAR",
            "Paquete de fuentes",
            pack.name,
            f"{len(created)} fuentes iniciales agregadas a {inventory.name}",
        )
    return created
