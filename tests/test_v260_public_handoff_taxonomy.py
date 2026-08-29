from __future__ import annotations

from app.public_web import _ALLOWED_OBJECTIVES, _ALLOWED_SECTORS


CURRENT_DIAGNOSIS_SECTORS = {
    "Manufactura",
    "Transporte y logística",
    "Servicios y oficinas",
    "Agroindustria",
    "Gestión de residuos",
    "Construcción",
    "Salud",
    "Energía",
    "Otro",
}

CURRENT_DIAGNOSIS_OBJECTIVES = {
    "Conocer la huella corporativa",
    "Requisito de clientes y estrategia de reducción",
    "Licitación o cadena de suministro",
    "Preparación para verificación",
    "Reporte regulatorio o sostenibilidad",
    "Información para dirección o financiadores",
}

LEGACY_SECTORS = {"Industria o manufactura"}
LEGACY_OBJECTIVES = {
    "Construir la primera huella",
    "Responder a cliente o licitación",
    "Gestionar un plan de reducción",
    "Preparar revisión externa",
}


def test_v260_contact_handoff_accepts_current_diagnosis_taxonomy() -> None:
    assert CURRENT_DIAGNOSIS_SECTORS <= _ALLOWED_SECTORS
    assert CURRENT_DIAGNOSIS_OBJECTIVES <= _ALLOWED_OBJECTIVES


def test_v260_contact_handoff_keeps_legacy_links_backward_compatible() -> None:
    assert LEGACY_SECTORS <= _ALLOWED_SECTORS
    assert LEGACY_OBJECTIVES <= _ALLOWED_OBJECTIVES
