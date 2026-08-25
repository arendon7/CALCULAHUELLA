from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from jinja2 import Environment, FileSystemLoader

from app.main import app


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "app" / "templates"
RESULT_TEMPLATE = TEMPLATES / "public_thanks.html"
INTERPRETATION_TEMPLATE = TEMPLATES / "public" / "diagnostic_interpretation.html"
ENGINE = ROOT / "app" / "services" / "product_intelligence.py"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _payload(email: str) -> dict[str, str]:
    return {
        "company_name": "Interpretación V2.60.3 S.A.S.",
        "contact_name": "Camila Interpretación",
        "email": email,
        "phone": "3004445566",
        "sector": "Manufactura",
        "city": "Medellín",
        "employees_band": "51 a 200",
        "facilities_count": "3",
        "countries_count": "1",
        "desired_scopes": "Alcances 1, 2 y 3 priorizado",
        "objective": "Preparación para verificación",
        "urgency": "Normal",
        "deadline_months": "6",
        "data_availability": "Parcial",
        "evidence_readiness": "Parcial",
        "reporting_frequency": "Trimestral",
        "assurance_ambition": "Preparación para verificación limitada",
        "uses_fuels": "on",
        "manages_waste": "on",
        "relies_on_suppliers": "on",
        "core_processes": "Producción, almacenamiento, despacho",
        "current_data_systems": "ERP, Excel, SharePoint",
        "notes": "Queremos ordenar evidencia antes de una revisión independiente.",
        "accept_privacy": "yes",
    }


def test_v2603_public_result_uses_qualitative_readiness_not_false_precision() -> None:
    template = _text(RESULT_TEMPLATE)

    assert "Cómo leer estos indicadores" in template
    assert "índices orientativos construidos a partir de respuestas declaradas" in template
    assert "No representan porcentajes de cumplimiento" in template
    assert "Preparación de datos" in template
    assert "Preparación para revisión externa" in template
    assert "Orientación de alistamiento; no acredita verificación ni aseguramiento" in template
    assert 'data_readiness_band(assessment.row.data_maturity_score)' in template
    assert 'review_readiness_band(assessment.row.verification_readiness_score)' in template

    assert "{{ assessment.row.data_maturity_score" not in template
    assert "{{ assessment.row.governance_maturity_score" not in template
    assert "{{ assessment.row.verification_readiness_score" not in template
    assert "puntos del diagnóstico" not in template
    assert "estimated_effort_hours" not in template


def test_v2603_interpretation_policy_has_explicit_stable_boundaries() -> None:
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=True)
    policy = env.get_template("public/diagnostic_interpretation.html").module

    assert str(policy.data_readiness_band(0)) == "Inicial"
    assert str(policy.data_readiness_band(39)) == "Inicial"
    assert str(policy.data_readiness_band(40)) == "En desarrollo"
    assert str(policy.data_readiness_band(59)) == "En desarrollo"
    assert str(policy.data_readiness_band(60)) == "Media"
    assert str(policy.data_readiness_band(79)) == "Media"
    assert str(policy.data_readiness_band(80)) == "Alta"
    assert str(policy.data_readiness_band(100)) == "Alta"

    assert str(policy.review_readiness_band(0)) == "Inicial"
    assert str(policy.review_readiness_band(49)) == "Inicial"
    assert str(policy.review_readiness_band(50)) == "En desarrollo"
    assert str(policy.review_readiness_band(69)) == "En desarrollo"
    assert str(policy.review_readiness_band(70)) == "Preparación alta"
    assert str(policy.review_readiness_band(100)) == "Preparación alta"

    assert str(policy.duration_reference(2)) == "2–3 meses"
    assert str(policy.duration_reference(6)) == "6–7 meses"


def test_v2603_public_result_curates_actions_instead_of_exposing_raw_engine_copy() -> None:
    template = _text(RESULT_TEMPLATE)

    assert "Decisiones que siguen abiertas" in template
    assert "Límites organizacionales y operacionales definitivos." in template
    assert "Factores, supuestos, exclusiones y criterios metodológicos aplicables." in template
    assert "Necesidad y alcance de una eventual revisión o verificación independiente." in template
    assert "assessment.exclusions" not in template
    assert "assessment.next_steps" not in template
    assert template.count("Validar el alcance") == 1
    assert template.count("Preparar la información") == 1
    assert template.count("Activar el inventario") == 1


def test_v2603_public_result_uses_public_plan_canon_not_database_label() -> None:
    template = _text(RESULT_TEMPLATE)

    assert "plan.name" not in template
    assert "{{ public_plan_name(lead.recommended_plan_code) }}" in template
    assert "{{ public_plan_description(lead.recommended_plan_code) }}" in template


def test_v2603_runtime_result_explains_limits_and_keeps_commercial_reference_bounded() -> None:
    email = "resultado-v2603@example.test"
    with TestClient(app) as client:
        created = client.post("/diagnostico", data=_payload(email), follow_redirects=False)
        assert created.status_code == 303
        result = client.get(created.headers["location"])

    assert result.status_code == 200
    assert "DIAGNÓSTICO ORIENTATIVO GENERADO" in result.text
    assert "Cómo leer estos indicadores" in result.text
    assert "No representan porcentajes de cumplimiento" in result.text
    assert "No es una huella calculada, una certificación ni una verificación independiente." in result.text
    assert "No constituye una cotización definitiva." in result.text
    assert "Gestión Corporativa" in result.text
    assert "Gestión Avanzada y Verificación" not in result.text
    assert "horas estimadas" not in result.text
    assert "puntos del diagnóstico" not in result.text


def test_v2603_internal_engine_keeps_exact_scores_for_traceability() -> None:
    engine = _text(ENGINE)

    assert "data_maturity_score=result.data_maturity_score" in engine
    assert "governance_maturity_score=result.governance_maturity_score" in engine
    assert "verification_readiness_score=result.verification_readiness_score" in engine
    assert "answers_json=_dump(payload)" in engine
