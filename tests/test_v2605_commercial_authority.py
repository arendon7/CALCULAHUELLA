from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.commercial_pricing import (
    proposal_first_year_total,
    proposal_initial_payment,
    subscription_custom_monthly_fee,
)
from app.db.base import SessionLocal
from app.db.models import (
    BillingInvoice,
    CommercialLead,
    CommercialProposal,
    OrganizationSubscription,
    PaymentTransaction,
    ServicePlan,
)
from app.main import app
from app.payment_web import _proposal_acceptance_source


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "app" / "templates" / "commercial.html"
PUBLIC_TEMPLATE = ROOT / "app" / "templates" / "public_proposal.html"
PAYMENT_TEMPLATE = ROOT / "app" / "templates" / "public_payment.html"
SOURCE = ROOT / "app" / "commercial_web.py"
PAYMENT_SOURCE = ROOT / "app" / "payment_web.py"
OPERATIONS_SOURCE = ROOT / "app" / "commercial_operations_web.py"


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


def _valid_payload(title: str, *, billing_cycle: str = "Anual") -> dict[str, str]:
    lead_id, plan_id = _lead_and_plan()
    return {
        "lead_id": str(lead_id),
        "plan_id": str(plan_id),
        "title": title,
        "implementation_fee": "1000000",
        "recurring_fee": "2000000",
        "discount_amount": "250000",
        "tax_rate": "19",
        "billing_cycle": billing_cycle,
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


def _proposal_by_title(title: str) -> CommercialProposal:
    with SessionLocal() as session:
        proposal = session.scalar(select(CommercialProposal).where(CommercialProposal.title == title))
        assert proposal is not None
        session.expunge(proposal)
        return proposal


def test_v2605_commercial_ui_has_explicit_offer_and_billing_authority() -> None:
    template = TEMPLATE.read_text(encoding="utf-8")
    public_template = PUBLIC_TEMPLATE.read_text(encoding="utf-8")
    payment_template = PAYMENT_TEMPLATE.read_text(encoding="utf-8")
    source = SOURCE.read_text(encoding="utf-8")
    payment_source = PAYMENT_SOURCE.read_text(encoding="utf-8")

    assert '{% from "public/plan_copy.html" import public_plan_name %}' in template
    assert "Autoridad de la oferta" in template
    assert "referencia diagnóstica" in template
    assert "plan contractual" in template.lower()
    assert "Los valores de campañas públicas tampoco se copian automáticamente" in template
    assert "valor por ciclo" in template.lower()
    assert "12 ciclos mensuales" in template
    assert "Descuento inicial" in template
    assert "lead.complexity_score" not in template

    for legacy in ("8500000", "9900000", "8 a 10 semanas"):
        assert legacy not in template

    assert 'name="tax_rate" value="19"' not in template
    assert 'name="implementation_fee"' in template and 'placeholder="Define el valor"' in template
    assert 'name="recurring_fee"' in template
    assert 'name="billing_cycle" required' in template
    assert 'name="valid_until"' in template and 'min="{{ proposal_min_valid_until }}"' in template

    assert "_parse_nonnegative_number" in source
    assert "proposal_first_year_total" in source
    assert 'contract_version="1.1"' in source
    assert "proposal_initial_payment" in source
    assert "recurring_first_year_value" in source
    assert "proposal_initial_payment" in payment_source
    assert "_ensure_supported_billing_contract" in payment_source
    assert "_proposal_acceptance_source" in payment_source
    assert "Pago de activación" in public_template
    assert "12 ciclos primer año" in public_template
    assert "Revisión comercial requerida" in public_template
    assert "Pago de activación" in payment_template


def test_v2605_billing_math_distinguishes_contract_value_from_activation_charge() -> None:
    assert proposal_first_year_total(1_000_000, 200_000, 100_000, 19, "Mensual") == 3_927_000
    assert proposal_initial_payment(1_000_000, 200_000, 100_000, 19) == 1_309_000
    assert proposal_first_year_total(1_000_000, 2_000_000, 250_000, 19, "Anual") == 3_272_500
    assert proposal_initial_payment(1_000_000, 2_000_000, 250_000, 19) == 3_272_500
    assert subscription_custom_monthly_fee(1_200_001, "Anual") * 12 == pytest.approx(1_200_001)


def test_v2605_acceptance_snapshot_binds_identity_scope_and_complete_economics() -> None:
    title = "V2.60.5 acceptance snapshot contract"
    payload = _valid_payload(title, billing_cycle="Mensual")
    payload.update(recurring_fee="200000", discount_amount="100000")

    with TestClient(app) as client:
        _login(client)
        assert client.post("/comercial/propuestas/nueva", data=payload, follow_redirects=False).status_code == 303

    proposal = _proposal_by_title(title)
    accepted_at = datetime(2026, 8, 24, 4, 30, tzinfo=UTC)
    baseline = _proposal_acceptance_source(
        proposal,
        "Valentina Gómez",
        "GERENCIA@CAFEDEMO.CO",
        accepted_at,
    )
    snapshot = json.loads(baseline)

    assert snapshot == {
        "reference": proposal.reference,
        "contract_version": "1.1",
        "billing_cycle": "Mensual",
        "implementation_fee": "1000000.00",
        "recurring_fee": "200000.00",
        "discount_amount": "100000.00",
        "tax_rate": "19.0000",
        "first_year_total": "3927000.00",
        "scope_json": proposal.scope_json,
        "deliverables_json": proposal.deliverables_json,
        "terms": proposal.terms,
        "accepted_by": "Valentina Gómez",
        "accepted_email": "gerencia@cafedemo.co",
        "accepted_at": accepted_at.isoformat(),
    }
    baseline_hash = hashlib.sha256(baseline.encode("utf-8")).hexdigest()

    mutations = {
        "billing_cycle": "Anual",
        "implementation_fee": proposal.implementation_fee + 1,
        "recurring_fee": proposal.recurring_fee + 1,
        "discount_amount": proposal.discount_amount + 1,
        "tax_rate": proposal.tax_rate + 0.01,
        "first_year_total": proposal.first_year_total + 1,
        "scope_json": '["Alcance alterado"]',
        "deliverables_json": '["Entregable alterado"]',
        "terms": proposal.terms + " Cambio.",
        "contract_version": "1.2",
    }
    for attribute, mutated_value in mutations.items():
        original = getattr(proposal, attribute)
        setattr(proposal, attribute, mutated_value)
        mutated = _proposal_acceptance_source(
            proposal,
            "Valentina Gómez",
            "gerencia@cafedemo.co",
            accepted_at,
        )
        assert hashlib.sha256(mutated.encode("utf-8")).hexdigest() != baseline_hash, attribute
        setattr(proposal, attribute, original)

    identity_variants = [
        ("Otra persona", "gerencia@cafedemo.co", accepted_at),
        ("Valentina Gómez", "otra@cafedemo.co", accepted_at),
        ("Valentina Gómez", "gerencia@cafedemo.co", accepted_at + timedelta(seconds=1)),
    ]
    for accepted_by, accepted_email, timestamp in identity_variants:
        mutated = _proposal_acceptance_source(proposal, accepted_by, accepted_email, timestamp)
        assert hashlib.sha256(mutated.encode("utf-8")).hexdigest() != baseline_hash


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
        ("valid_until", "not-a-date", "La fecha de vigencia no es válida"),
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


def test_v2605_discount_cannot_exceed_activation_subtotal() -> None:
    title = "V2.60.5 excessive discount"
    payload = _valid_payload(title)
    payload["implementation_fee"] = "100"
    payload["recurring_fee"] = "200"
    payload["discount_amount"] = "301"

    with TestClient(app) as client:
        _login(client)
        response = client.post("/comercial/propuestas/nueva", data=payload, follow_redirects=False)

    assert response.status_code == 400
    assert "descuento inicial no puede superar el primer cobro" in response.text.lower()
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


def test_v2605_valid_annual_offer_preserves_existing_total_contract() -> None:
    title = "V2.60.5 explicit annual offer"
    payload = _valid_payload(title)

    with TestClient(app) as client:
        _login(client)
        response = client.post("/comercial/propuestas/nueva", data=payload, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/comercial"

    proposal = _proposal_by_title(title)
    assert proposal.implementation_fee == 1_000_000
    assert proposal.recurring_fee == 2_000_000
    assert proposal.discount_amount == 250_000
    assert proposal.tax_rate == 19
    assert proposal.billing_cycle == "Anual"
    assert proposal.first_year_total == 3_272_500
    assert proposal.valid_until == date.today() + timedelta(days=30)
    assert proposal.status == "Borrador"
    assert proposal.contract_version == "1.1"

    with TestClient(app) as client:
        public = client.get(f"/propuesta/{proposal.public_token}")
        assert public.status_code == 200
        assert title in public.text
        assert "En ciclo anual coincide con la inversión del primer año" in public.text


def test_v2605_monthly_offer_annualizes_contract_but_charges_only_activation_cycle() -> None:
    title = "V2.60.5 monthly billing authority"
    payload = _valid_payload(title, billing_cycle="Mensual")
    payload.update(
        implementation_fee="1000000",
        recurring_fee="200000",
        discount_amount="100000",
        tax_rate="19",
    )

    with TestClient(app) as client:
        _login(client)
        created = client.post("/comercial/propuestas/nueva", data=payload, follow_redirects=False)
        assert created.status_code == 303
        proposal = _proposal_by_title(title)
        assert proposal.first_year_total == 3_927_000

        public = client.get(f"/propuesta/{proposal.public_token}")
        assert public.status_code == 200
        assert "12 ciclos primer año" in public.text
        assert "2.400.000" in public.text
        assert "1.309.000" in public.text

        accepted = client.post(
            f"/propuesta/{proposal.public_token}/aceptar",
            data={
                "accepted_by": "Valentina Gómez",
                "accepted_email": "gerencia@cafedemo.co",
                "accept_terms": "on",
            },
            follow_redirects=False,
        )
        assert accepted.status_code == 303
        assert accepted.headers["location"].startswith("/pago/")
        payment_token = accepted.headers["location"].rsplit("/", 1)[-1]

        with SessionLocal() as session:
            payment = session.scalar(select(PaymentTransaction).where(PaymentTransaction.public_token == payment_token))
            assert payment is not None
            assert payment.amount == 1_309_000
            assert payment.amount != proposal.first_year_total
            accepted_proposal = session.get(CommercialProposal, proposal.id)
            assert accepted_proposal is not None
            assert accepted_proposal.accepted_at is not None
            expected_source = _proposal_acceptance_source(
                accepted_proposal,
                accepted_proposal.accepted_by,
                accepted_proposal.accepted_email,
                accepted_proposal.accepted_at,
            )
            assert accepted_proposal.acceptance_hash == hashlib.sha256(expected_source.encode("utf-8")).hexdigest()

        payment_page = client.get(f"/pago/{payment_token}")
        assert payment_page.status_code == 200
        assert "No representa el valor completo del primer año" in payment_page.text

        confirmed = client.post(
            f"/pago/{payment_token}/confirmar",
            data={"payer_name": "Valentina Gómez", "payer_email": "gerencia@cafedemo.co"},
            follow_redirects=False,
        )
        assert confirmed.status_code == 303

    with SessionLocal() as session:
        payment = session.scalar(select(PaymentTransaction).where(PaymentTransaction.public_token == payment_token))
        assert payment is not None
        assert payment.subscription_id is not None
        subscription = session.get(OrganizationSubscription, payment.subscription_id)
        assert subscription is not None
        assert subscription.billing_cycle == "Mensual"
        assert subscription.custom_monthly_fee == 200_000
        assert "valor base recurrente negociado" in subscription.notes
        assert "Impuesto contractual de 19%" in subscription.notes
        invoice = session.get(BillingInvoice, payment.invoice_id)
        assert invoice is not None
        assert invoice.amount == 1_309_000
        assert invoice.period_end < date(date.today().year + 1, date.today().month, min(date.today().day, 28))


def test_v2605_legacy_monthly_proposal_cannot_be_accepted() -> None:
    title = "V2.60.5 legacy monthly guard"
    payload = _valid_payload(title, billing_cycle="Mensual")
    payload["recurring_fee"] = "200000"

    with TestClient(app) as client:
        _login(client)
        assert client.post("/comercial/propuestas/nueva", data=payload, follow_redirects=False).status_code == 303
        proposal = _proposal_by_title(title)
        with SessionLocal() as session:
            stored = session.get(CommercialProposal, proposal.id)
            assert stored is not None
            stored.contract_version = "1.0"
            session.commit()

        public = client.get(f"/propuesta/{proposal.public_token}")
        assert public.status_code == 200
        assert "Revisión comercial requerida" in public.text
        assert "Aceptar propuesta" not in public.text

        rejected = client.post(
            f"/propuesta/{proposal.public_token}/aceptar",
            data={"accepted_by": "Valentina Gómez", "accepted_email": "gerencia@cafedemo.co", "accept_terms": "on"},
            follow_redirects=False,
        )
        assert rejected.status_code == 409
        assert "versión contractual anterior" in rejected.text

    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(PaymentTransaction).where(PaymentTransaction.proposal_id == proposal.id)) == 0


def test_v2605_recurring_invoice_uses_negotiated_zero_instead_of_catalog_fallback() -> None:
    operations_source = OPERATIONS_SOURCE.read_text(encoding="utf-8")
    assert "subscription.custom_monthly_fee is not None" in operations_source
    assert "subscription.custom_monthly_fee or subscription.plan.monthly_fee" not in operations_source
