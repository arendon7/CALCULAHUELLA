from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


pytestmark = pytest.mark.smoke
ROOT = Path(__file__).resolve().parents[1]


def test_v150_public_home_loads_context_producer_and_keeps_progressive_fallback():
    with TestClient(app) as client:
        home = client.get("/")
        producer = client.get("/static/js/landing_context.js")
        stylesheet = client.get("/static/css/landing_context.css")

    assert home.status_code == 200
    assert producer.status_code == 200
    assert stylesheet.status_code == 200
    assert "landing_context.js" in home.text
    assert "landing_context.css" in home.text
    assert 'class="public-audience-strip"' in home.text
    assert 'href="/diagnostico"' in home.text  # fallback sin JavaScript


def test_v150_producer_and_consumer_share_the_same_versioned_contract():
    producer = (ROOT / "app/static/js/landing_context.js").read_text(encoding="utf-8")
    consumer = (ROOT / "app/static/js/diagnosis_handoff.js").read_text(encoding="utf-8")

    for token in ("cth_landing_context_v1", "cth.landing_context.v1"):
        assert token in producer
        assert token in consumer

    assert "reusable: { sector, objective }" in producer
    assert 'select[name="sector"]' in consumer
    assert 'select[name="objective"]' in consumer
    assert "window.location.assign('/diagnostico')" in producer


def test_v150_every_prefill_value_exists_in_the_real_diagnosis_form():
    producer = (ROOT / "app/static/js/landing_context.js").read_text(encoding="utf-8")
    diagnosis = (ROOT / "app/templates/public_diagnosis.html").read_text(encoding="utf-8")

    expected_sectors = (
        "Servicios y oficinas",
        "Manufactura",
        "Agroindustria",
        "Transporte y logística",
        "Gestión de residuos",
        "Construcción",
        "Salud",
        "Energía",
        "Otro",
    )
    expected_objectives = (
        "Conocer la huella corporativa",
        "Requisito de clientes y estrategia de reducción",
        "Licitación o cadena de suministro",
        "Preparación para verificación",
        "Reporte regulatorio o sostenibilidad",
        "Información para dirección o financiadores",
    )
    for value in (*expected_sectors, *expected_objectives):
        assert value in producer
        assert value in diagnosis


def test_v150_landing_context_contains_no_personal_or_methodological_fields():
    producer = (ROOT / "app/static/js/landing_context.js").read_text(encoding="utf-8")

    for forbidden in (
        "company_name",
        "contact_name",
        "email",
        "phone",
        "notes",
        "desired_scopes",
        "assurance_ambition",
        "deadline_months",
        "commercial_interest",
        "recommended_plan",
    ):
        assert forbidden not in producer


def test_v150_home_cta_is_progressively_enhanced_not_replaced_server_side():
    template = (ROOT / "app/templates/public_home.html").read_text(encoding="utf-8")
    producer = (ROOT / "app/static/js/landing_context.js").read_text(encoding="utf-8")

    assert 'class="public-hero v049-hero"' in template
    assert 'href="/diagnostico">Recibir diagnóstico inicial' in template
    assert "primaryHeroCta.href = '#preconfiguracion'" in producer
    assert "primaryHeroCta.textContent = 'Preconfigurar diagnóstico'" in producer
    assert "anchor.insertAdjacentElement('afterend', section)" in producer
