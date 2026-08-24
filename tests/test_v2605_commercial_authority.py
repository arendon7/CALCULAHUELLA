from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.base import SessionLocal
from app.db.models import CommercialLead, CommercialProposal, ServicePlan
from app.main import app


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "app" / "templates" / "commercial.html"
SOURCE = ROOT / "app" / "commercial_web.py"


def _login(client: TestClient) -> None:
    response = client.post(
        "/login",
        data={"email": "admin@calculatuhuella.local", "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def _lead_and_plan() -> tuple[int, int]:
    with SessionLocal() as session:
        lead = session.scalar(select(CommercialLead).order_by(CommercialLead.id))
        plan = session.scalar(
            select(ServicePlan).where(ServicePlan.active.is_(True)).order_by(ServicePlan.id)
        )
        assert lead is not None
        assert plan is not None
        return lead.id, plan.id


def _valid_payload(title: str) -> dict[str, str]:
    lead_id, plan_id = _lead_and_plan()
    return {
        "lead_id": str(lead_id),
        "plan_id": str(plan_id),
        "title": title,
        "implementation_fee": "1000000",
        "recurring_fee": "2000000",
        "discount_amount": "250000",
        "tax_rate": "19",
        "billing_cycle": "Anual",
        "valid_until": (date.today() + timedelta(days=30)).isoformat(),
        "scope": "Alcances 1 y 2\nSedes acordadas",
        "deliverables": "Inventario corporativo\nMemoria de cálculo",
        "terms": "Vigencia y dependencias acordadas. La verificación independiente no está incluida.",
    }


def _proposal_count(title: str) -> int:
    with SessionLocal() as session:
        return int(
            session.scalar(
                select(func.count()).select_from(CommercialProposal).where(CommercialProposal.title == title)
            )
            or 0
        )


def test_v2605_commercial_ui_has_explicit_offer_authority_and_no_legacy_defaults() -> None:
    template = TEMPLATE.read_text(encoding="utf-8")
    source = SOURCE.read_text(encoding="utf-8")

    assert '{% from "public/plan_copy.html" import public_plan_name %}' in template
    assert "Autoridad de la oferta" in template
    assert "referencia diagnóstica" in template
    assert "plan contractual" in template.lower()
    assert "Los valores de campañas públicas tampoco se copian automáticamente" in template
    assert "lead.complexity_score" not in template

    for legacy in ("8500000", "9900000", "8 a 10 semanas"):
        assert legacy not in template

    assert 'name="tax_rate" value="19"' not in template
    assert 'name="implementation_fee"' in template and 'placeholder="Define el valor"' in template
    assert 'name="recurring_fee"' in template
    assert 'name="billing_cycle" required' in template
    assert 'name="valid_until"' in template and 'min="{{ proposal_min_valid_until }}"' in template

    assert "_parse_nonnegative_number" in source
    assert 'billing_cycle if billing_cycle in {"Mensual", "Anual"} else "Anual"' not in source
    assert "implementation_fee=max(0" not in source
    assert "recurring_fee=max(0" not in source
    assert "discount_amount=max(0" not in source
    assert "tax_rate=max(0" not in source


def test_v2605_missing_explicit_amount_returns_400_preserves_form_and_does_not_persist() -> None:
    title = "V2.60.5 missing implementation authority"
    payload = _valid_payload(title)
    payload["implementation_fee"] = ""
    lead_id = payload["lead_id"]
    plan_id = payload["plan_id"]

    with TestClient(app) as client:
        _login(client)
        response = client.post("/comercial/propuestas/nueva", data=payload, follow_redirects=False)

    assert response.status_code == 400
    assert "No se creó la propuesta" in response.text
    assert "Define el valor de implementación" in response.text
    assert title in response.text
    assert f'value="{lead_id}" selected' in response.text
    assert f'value="{plan_id}" selected' in response.text
    assert _proposal_count(title) == 0


@pytest.mark.parametrize(
    ("field", "value", "expected_message"),
    [
        ("implementation_fee", "-1", "no puede ser negativo"),
        ("tax_rate", "nan", "debe ser un número finito"),
        ("tax_rate", "101", "no puede ser mayor que 100"),
        ("billing_cycle", "Semanal", "Selecciona un ciclo de facturación válido"),
    ],
)
def test_v2605_invalid_contractual_values_are_rejected_without_silent_coercion(
    field: str,
    value: str,
    expected_message: str,
) -> None:
    title = f"V2.60.5 reject {field} {value}"
    payload = _valid_payload(title)
    payload[field] = value

    with TestClient(app) as client:
        _login(client)
        response = client.post("/comercial/propuestas/nueva", data=payload, follow_redirects=False)

    assert response.status_code == 400
    assert expected_message in response.text
    assert _proposal_count(title) == 0


def test_v2605_discount_cannot_exceed_explicit_subtotal() -> None:
    title = "V2.60.5 excessive discount"
    payload = _valid_payload(title)
    payload["implementation_fee"] = "100"
    payload["recurring_fee"] = "200"
    payload["discount_amount"] = "301"

    with TestClient(app) as client:
        _login(client)
        response = client.post("/comercial/propuestas/nueva", data=payload, follow_redirects=False)

    assert response.status_code == 400
    assert "El descuento no puede superar" in response.text
    assert _proposal_count(title) == 0


def test_v2605_proposal_validity_cannot_be_in_the_past() -> None:
    title = "V2.60.5 past validity"
    payload = _valid_payload(title)
    payload["valid_until"] = (date.today() - timedelta(days=1)).isoformat()

    with TestClient(app) as client:
        _login(client)
        response = client.post("/comercial/propuestas/nueva", data=payload, follow_redirects=False)

    assert response.status_code == 400
    assert "no puede estar en el pasado" in response.text
    assert _proposal_count(title) == 0


def test_v2605_valid_explicit_offer_preserves_values_and_existing_transaction_contract() -> None:
    title = "V2.60.5 explicit commercial offer"
    payload = _valid_payload(title)

    with TestClient(app) as client:
        _login(client)
        response = client.post("/comercial/propuestas/nueva", data=payload, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/comercial"

    with SessionLocal() as session:
        proposal = session.scalar(
            select(CommercialProposal).where(CommercialProposal.title == title)
        )
        assert proposal is not None
        assert proposal.implementation_fee == 1_000_000
        assert proposal.recurring_fee == 2_000_000
        assert proposal.discount_amount == 250_000
        assert proposal.tax_rate == 19
        assert proposal.billing_cycle == "Anual"
        assert proposal.first_year_total == 3_272_500
        assert proposal.valid_until == date.today() + timedelta(days=30)
        assert proposal.status == "Borrador"
        assert proposal.public_token
        token = proposal.public_token

    with TestClient(app) as client:
        public = client.get(f"/propuesta/{token}")
        assert public.status_code == 200
        assert title in public.text
