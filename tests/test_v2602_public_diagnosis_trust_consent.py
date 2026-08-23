from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.config import settings
from app.database import CommercialLead, DiagnosticAssessment, SessionLocal
from app.main import app


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "app" / "templates" / "public_diagnosis.html"
ENGINE = ROOT / "app" / "product_intelligence_web.py"
WIZARD_JS = ROOT / "app" / "static" / "js" / "public-diagnosis-v260.js"
HANDOFF_JS = ROOT / "app" / "static" / "js" / "diagnosis_handoff.js"
HANDOFF_CSS = ROOT / "app" / "static" / "css" / "diagnosis_handoff.css"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _payload(email: str) -> dict[str, str]:
    return {
        "company_name": "Empresa Consentimiento S.A.S.",
        "contact_name": "Laura Consentimiento",
        "email": email,
        "phone": "3001112233",
        "sector": "Manufactura",
        "city": "Medellín",
        "employees_band": "21 a 50",
        "facilities_count": "2",
        "countries_count": "1",
        "desired_scopes": "Alcances 1, 2 y 3 priorizado",
        "objective": "Conocer la huella corporativa",
        "urgency": "Normal",
        "deadline_months": "6",
        "data_availability": "Media",
        "evidence_readiness": "Parcial",
        "reporting_frequency": "Anual",
        "assurance_ambition": "Sin verificación externa",
        "uses_fuels": "on",
        "manages_waste": "on",
        "core_processes": "Producción, almacenamiento",
        "current_data_systems": "ERP, Excel",
        "notes": "Necesitamos ordenar el inventario inicial.",
    }


def test_v2602_diagnosis_ui_requires_explicit_privacy_authorization() -> None:
    template = _text(TEMPLATE)
    css = _text(HANDOFF_CSS)

    assert 'name="accept_privacy" value="yes" required' in template
    assert "Autorizo el tratamiento de estos datos" in template
    assert 'href="/legal/privacidad"' in template
    assert "Al generar el resultado aceptas" not in template
    assert ".diagnosis-consent input" in css
    assert ".diagnosis-consent input:focus-visible" in css


def test_v2602_server_rejects_missing_privacy_consent_before_persistence_and_preserves_form() -> None:
    email = "sin-consentimiento-v2602@example.test"
    with SessionLocal() as session:
        leads_before = session.scalar(select(func.count()).select_from(CommercialLead))
        assessments_before = session.scalar(select(func.count()).select_from(DiagnosticAssessment))

    with TestClient(app) as client:
        response = client.post("/diagnostico", data=_payload(email), follow_redirects=False)

    assert response.status_code == 400
    assert "Debes autorizar el tratamiento de datos" in response.text
    assert 'data-diagnosis-initial-step="4"' in response.text
    assert 'value="Empresa Consentimiento S.A.S."' in response.text
    assert f'value="{email}"' in response.text
    assert "Necesitamos ordenar el inventario inicial." in response.text

    with SessionLocal() as session:
        leads_after = session.scalar(select(func.count()).select_from(CommercialLead))
        assessments_after = session.scalar(select(func.count()).select_from(DiagnosticAssessment))
        rejected = session.scalar(select(CommercialLead).where(CommercialLead.email == email))

    assert leads_after == leads_before
    assert assessments_after == assessments_before
    assert rejected is None


def test_v2602_authorized_diagnosis_persists_legal_version_with_lead() -> None:
    email = "consentimiento-v2602@example.test"
    payload = _payload(email)
    payload["accept_privacy"] = "yes"

    with TestClient(app) as client:
        response = client.post("/diagnostico", data=payload, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/diagnostico/gracias/")

    with SessionLocal() as session:
        lead = session.scalar(select(CommercialLead).where(CommercialLead.email == email))
        assert lead is not None
        assessment = session.scalar(select(DiagnosticAssessment).where(DiagnosticAssessment.lead_id == lead.id))
        assert assessment is not None
        assert f"Autorización de privacidad: sí · versión {settings.legal_effective_date}" in lead.notes
        assert "Necesitamos ordenar el inventario inicial." in lead.notes


def test_v2602_diagnosis_uses_dedicated_reduced_motion_and_csp_safe_controller() -> None:
    template = _text(TEMPLATE)
    legacy_bundle = _text(ROOT / "app" / "static" / "js" / "app.js")
    wizard = _text(WIZARD_JS)
    css = _text(HANDOFF_CSS)

    assert "data-v260-diagnosis-wizard" in template
    assert "data-diagnosis-wizard" not in template
    assert "js/public-diagnosis-v260.js" in template
    assert "document.querySelector('[data-diagnosis-wizard]')" in legacy_bundle
    assert "document.querySelector('[data-v260-diagnosis-wizard]')" in wizard
    assert "prefers-reduced-motion: reduce" in wizard
    assert "reducedMotion ? 'auto' : 'smooth'" in wizard
    assert "data-diagnosis-initial-step" in template
    assert "form.dataset.diagnosisProgressStep" in wizard
    assert ".style.width" not in wizard
    for step, width in ((1, 25), (2, 50), (3, 75), (4, 100)):
        assert f'data-diagnosis-progress-step="{step}"' in css
        assert f"width: {width}%" in css


def test_v2602_landing_handoff_targets_new_wizard_without_overwriting_rejected_form() -> None:
    handoff = _text(HANDOFF_JS)

    assert "[data-v260-diagnosis-wizard], [data-diagnosis-wizard]" in handoff
    assert "const restoringRejectedForm = Boolean(form.querySelector('[role=\"alert\"]'));" in handoff
    assert "if (restoringRejectedForm) return 0;" in handoff
    assert handoff.index("if (restoringRejectedForm) return 0;") < handoff.index("Object.entries(allowed)")


def test_v2602_backend_contract_validates_consent_before_assessment_creation() -> None:
    engine = _text(ENGINE)

    assert "accept_privacy: str | None = Form(None)" in engine
    assert 'if accept_privacy != "yes":' in engine
    assert "Autorización de privacidad: sí · versión" in engine
    assert engine.index('if accept_privacy != "yes":') < engine.index("create_assessment(session, payload=payload")
