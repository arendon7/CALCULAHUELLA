from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


pytestmark = pytest.mark.smoke
ROOT = Path(__file__).resolve().parents[1]
PUBLIC_JS = ROOT / "app/static/js/public-v1.6.js"
CONSUMER_JS = ROOT / "app/static/js/diagnosis_handoff.js"
CONSUMER_CSS = ROOT / "app/static/css/diagnosis_handoff.css"
PRECONFIG = ROOT / "app/templates/public/v14/experience_resources_cta.html"
DIAGNOSIS = ROOT / "app/templates/public_diagnosis.html"
PUBLIC_BASE = ROOT / "app/templates/public_base.html"


def test_v160_public_home_exposes_two_decision_preconfiguration_and_real_fallback():
    with TestClient(app) as client:
        home = client.get("/")
        consumer = client.get("/static/js/diagnosis_handoff.js")
        stylesheet = client.get("/static/css/diagnosis_handoff.css")

    assert home.status_code == 200
    assert consumer.status_code == 200
    assert stylesheet.status_code == 200
    assert 'data-landing-context-form' in home.text
    assert 'name="landing_sector"' in home.text
    assert 'name="landing_objective"' in home.text
    assert 'href="/diagnostico"' in home.text


def test_v160_producer_and_consumer_share_versioned_contract_and_internal_destination():
    producer = PUBLIC_JS.read_text(encoding="utf-8")
    consumer = CONSUMER_JS.read_text(encoding="utf-8")

    for token in ("cth_landing_context_v1", "cth.landing_context.v1"):
        assert token in producer
        assert token in consumer

    assert "reusable: { sector, objective }" in producer
    assert "destination: '/diagnostico'" in producer
    assert "window.location.assign('/diagnostico')" in producer
    assert 'select[name="sector"]' in consumer
    assert 'select[name="objective"]' in consumer
    assert "30 * 60 * 1000" in consumer


def test_v160_every_prefill_value_exists_in_real_diagnosis_selects():
    preconfig = PRECONFIG.read_text(encoding="utf-8")
    diagnosis = DIAGNOSIS.read_text(encoding="utf-8")

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
        assert value in preconfig
        assert value in diagnosis


def test_v160_reusable_context_contains_no_personal_or_commercial_fields():
    producer = PUBLIC_JS.read_text(encoding="utf-8")
    contract_start = producer.index("const context = {")
    contract_end = producer.index("};", contract_start) + 2
    contract = producer[contract_start:contract_end]

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
        assert forbidden not in contract
    assert "reusable: { sector, objective }" in contract


def test_v160_consumer_whitelists_only_sector_and_objective_and_keeps_fields_editable():
    consumer = CONSUMER_JS.read_text(encoding="utf-8")
    assert "const allowed = {" in consumer
    assert 'sector: form.querySelector(\'select[name="sector"]\')' in consumer
    assert 'objective: form.querySelector(\'select[name="objective"]\')' in consumer
    assert "company_name" not in consumer
    assert "email" not in consumer
    assert "disabled" not in consumer
    assert "Puedes cambiarlos antes de enviar" in consumer


def test_v160_public_base_loads_handoff_assets_once():
    html = PUBLIC_BASE.read_text(encoding="utf-8")
    assert html.count("diagnosis_handoff.css") == 1
    assert html.count("diagnosis_handoff.js") == 1
    assert CONSUMER_CSS.is_file()
