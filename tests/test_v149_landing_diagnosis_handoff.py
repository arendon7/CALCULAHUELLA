from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.smoke


def test_v149_public_diagnosis_loads_isolated_handoff_assets():
    with TestClient(app) as client:
        response = client.get("/diagnostico")
        javascript = client.get("/static/js/diagnosis_handoff.js")
        stylesheet = client.get("/static/css/diagnosis_handoff.css")

    assert response.status_code == 200
    assert javascript.status_code == 200
    assert stylesheet.status_code == 200
    assert "diagnosis_handoff.js" in response.text
    assert "diagnosis_handoff.css" in response.text
    assert 'name="sector"' in response.text
    assert 'name="objective"' in response.text


def test_v149_context_is_versioned_short_lived_and_whitelist_only():
    javascript = (ROOT / "app/static/js/diagnosis_handoff.js").read_text(encoding="utf-8")

    assert "cth_landing_context_v1" in javascript
    assert "cth.landing_context.v1" in javascript
    assert "30 * 60 * 1000" in javascript
    assert "age < 0" in javascript
    assert 'select[name="sector"]' in javascript
    assert 'select[name="objective"]' in javascript
    assert "context.reusable" in javascript

    for forbidden_selector in (
        'input[name="company_name"]',
        'input[name="contact_name"]',
        'input[name="email"]',
        'input[name="phone"]',
        'textarea[name="notes"]',
        'select[name="desired_scopes"]',
        'select[name="assurance_ambition"]',
        'select[name="deadline_months"]',
    ):
        assert forbidden_selector not in javascript


def test_v149_commercial_interest_cannot_drive_diagnosis_fields():
    javascript = (ROOT / "app/static/js/diagnosis_handoff.js").read_text(encoding="utf-8")
    assert "commercial_interest" not in javascript
    assert "recommended_plan" not in javascript


def test_v149_prefill_notice_is_created_only_after_a_valid_field_is_applied():
    javascript = (ROOT / "app/static/js/diagnosis_handoff.js").read_text(encoding="utf-8")
    assert "if (!form || applied < 1" in javascript
    assert "Continuamos desde la landing." in javascript
    assert "Puedes cambiarlos antes de enviar." in javascript
    assert "role', 'status'" in javascript
    assert "aria-live', 'polite'" in javascript


def test_v149_handoff_does_not_modify_global_app_javascript():
    public_base = (ROOT / "app/templates/public_base.html").read_text(encoding="utf-8")
    assert "js/app.js" in public_base
    assert "js/diagnosis_handoff.js" in public_base
    assert "css/diagnosis_handoff.css" in public_base
