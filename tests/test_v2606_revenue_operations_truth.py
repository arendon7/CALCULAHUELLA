from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.commercial_pricing import proposal_first_year_total
from app.database import SessionLocal
from app.db.models import (
    BillingChargeBreakdown,
    BillingInvoice,
    CollectionAction,
    CommercialLead,
    CommercialProposal,
    ContractSignatureSnapshot,
    Organization,
    OrganizationSubscription,
    PaymentTransaction,
    ServiceContract,
    ServicePlan,
)
from app.main import app
from app.revenue_operations import (
    CONTRACT_SIGNATURE_VERSION,
    INVOICE_BASE_BEFORE_TAX,
    INVOICE_TOTAL_WITH_TAX,
    contract_signature_hash,
    contract_signature_source,
    parse_nonnegative_number,
)


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "migrations" / "versions" / "20260824_0041_v2606_revenue_operations_truth.py"
TEMPLATE = ROOT / "app" / "templates" / "commercial_operations.html"


def login(client: TestClient, email: str = "consultor@calculatuhuella.local") -> None:
    response = client.post("/login", data={"email": email, "password": "Demo2026!"}, follow_redirects=False)
    assert response.status_code == 303


def _unique(prefix: str) -> str:
    return f"{prefix}-{date.today().strftime('%Y%m%d')}"


def test_v2606_revenue_migration_is_explicit_idempotent_and_non_destructive() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    assert 'revision = "20260824_0041"' in source
    assert 'down_revision = "20260812_0040"' in source
    assert 'if "billing_charge_breakdowns" not in tables' in source
    assert 'if "contract_signature_snapshots" not in tables' in source
    assert 'sa.UniqueConstraint("invoice_id"' in source
    assert 'sa.UniqueConstraint("contract_id"' in source
    assert "def downgrade()" in source and "return" in source.split("def downgrade()", 1)[1]
    assert "Numeric" not in source


def test_v2606_nonnegative_parser_fails_closed_for_invalid_money() -> None:
    assert parse_nonnegative_number("123.45", "el valor") == pytest.approx(123.45)
    for bad in ("", "-0.01", "nan", "NaN", "inf", "-inf", "texto"):
        with pytest.raises(ValueError):
            parse_nonnegative_number(bad, "el valor")


def test_v2606_contract_rejects_cross_organization_proposal_without_persistence() -> None:
    with SessionLocal() as session:
        organizations = list(session.scalars(select(Organization).order_by(Organization.id).limit(2)))
        assert len(organizations) >= 2
        plan = session.scalar(select(ServicePlan).where(ServicePlan.active.is_(True)).order_by(ServicePlan.id))
        lead = session.scalar(select(CommercialLead).order_by(CommercialLead.id))
        assert plan is not None and lead is not None
        proposal = CommercialProposal(
            lead_id=lead.id,
            organization_id=organizations[0].id,
            plan_id=plan.id,
            reference=_unique("PROP-CROSS"),
            public_token=_unique("TOKEN-CROSS"),
            title="Propuesta cross tenant",
            company_name=organizations[0].name,
            status="Aceptada",
            valid_until=date.today() + timedelta(days=30),
            billing_cycle="Anual",
            implementation_fee=1000,
            recurring_fee=2000,
            discount_amount=0,
            tax_rate=19,
            first_year_total=3570,
            scope_json='["Alcance"]',
            deliverables_json='["Entregable"]',
            terms="Condiciones",
            contract_version="1.1",
        )
        session.add(proposal)
        session.commit()
        proposal_id = proposal.id
        wrong_org_id = organizations[1].id
        before = session.scalar(select(func.count()).select_from(ServiceContract))

    with TestClient(app) as client:
        login(client)
        response = client.post(
            "/operacion-comercial/contratos/nuevo",
            data={
                "organization_id": wrong_org_id,
                "proposal_id": str(proposal_id),
                "title": "No debe persistir",
                "start_date": date.today().isoformat(),
                "contract_value": "1000",
                "billing_cycle": "Anual",
                "renewal_type": "Anual",
                "notice_days": "30",
            },
            follow_redirects=False,
        )
        assert response.status_code == 409

    with SessionLocal() as session:
        after = session.scalar(select(func.count()).select_from(ServiceContract))
        assert after == before


def test_v2606_contract_inputs_reject_silent_coercion() -> None:
    with SessionLocal() as session:
        organization = session.scalar(select(Organization).order_by(Organization.id))
        assert organization is not None
        organization_id = organization.id
        before = session.scalar(select(func.count()).select_from(ServiceContract))

    base = {
        "organization_id": organization_id,
        "proposal_id": "",
        "title": "Contrato fail closed",
        "start_date": "2026-09-10",
        "end_date": "2026-12-10",
        "contract_value": "1000",
        "billing_cycle": "Anual",
        "renewal_type": "Anual",
        "notice_days": "30",
    }
    bad_cases = [
        {"contract_value": "-1"},
        {"contract_value": "nan"},
        {"billing_cycle": "Trimestral"},
        {"renewal_type": "Automática mágica"},
        {"notice_days": "-1"},
        {"notice_days": "1.5"},
        {"start_date": "2026-12-10", "end_date": "2026-09-10"},
    ]
    with TestClient(app) as client:
        login(client)
        for patch in bad_cases:
            payload = dict(base)
            payload.update(patch)
            response = client.post("/operacion-comercial/contratos/nuevo", data=payload, follow_redirects=False)
            assert response.status_code == 400, (patch, response.text)

    with SessionLocal() as session:
        after = session.scalar(select(func.count()).select_from(ServiceContract))
        assert after == before


def test_v2606_new_contract_signature_snapshot_is_complete_and_roundtrip_stable() -> None:
    reference = _unique("CTR-V2606")
    with SessionLocal() as session:
        organization = session.scalar(select(Organization).order_by(Organization.id))
        assert organization is not None
        organization_id = organization.id

    with TestClient(app) as client:
        login(client)
        created = client.post(
            "/operacion-comercial/contratos/nuevo",
            data={
                "organization_id": organization_id,
                "proposal_id": "",
                "reference": reference,
                "title": "Contrato con snapshot completo",
                "start_date": "2026-09-01",
                "end_date": "2027-08-31",
                "contract_value": "1234567.89",
                "billing_cycle": "Anual",
                "renewal_type": "Por acuerdo",
                "notice_days": "45",
                "auto_renew": "1",
                "owner": "Dirección comercial",
                "terms_snapshot": "Alcance y condiciones V2.60.6",
            },
            follow_redirects=False,
        )
        assert created.status_code == 303
        with SessionLocal() as session:
            contract = session.scalar(select(ServiceContract).where(ServiceContract.reference == reference))
            assert contract is not None
            contract_id = contract.id
        signed = client.post(
            f"/operacion-comercial/contratos/{contract_id}/firmar",
            data={"signed_by": "Laura Firma", "signed_email": "laura@example.com"},
            follow_redirects=False,
        )
        assert signed.status_code == 303

    with SessionLocal() as session:
        contract = session.get(ServiceContract, contract_id)
        snapshot = session.scalar(select(ContractSignatureSnapshot).where(ContractSignatureSnapshot.contract_id == contract_id))
        assert contract is not None and snapshot is not None and contract.signed_at is not None
        assert snapshot.signature_version == CONTRACT_SIGNATURE_VERSION
        assert contract.signature_hash == snapshot.payload_hash
        assert contract_signature_hash(contract, contract.signed_by, contract.signed_email, contract.signed_at) == contract.signature_hash
        assert contract_signature_source(contract, contract.signed_by, contract.signed_email, contract.signed_at) == snapshot.canonical_payload
        payload = json.loads(snapshot.canonical_payload)
        assert payload["signature_version"] == "1.1"
        assert payload["title"] == contract.title
        assert payload["renewal_type"] == "Por acuerdo"
        assert payload["auto_renew"] is True
        assert payload["notice_days"] == 45
        assert payload["owner"] == "Dirección comercial"
        assert payload["terms_snapshot"] == "Alcance y condiciones V2.60.6"
        assert payload["contract_value"] == "1234567.89"


def test_v2606_legacy_signature_is_not_rehashed_automatically() -> None:
    with SessionLocal() as session:
        legacy = session.scalar(
            select(ServiceContract)
            .where(ServiceContract.signature_hash != "")
            .order_by(ServiceContract.id)
        )
        if legacy is None:
            pytest.skip("La semilla no contiene firma contractual legacy")
        before_hash = legacy.signature_hash
        legacy_id = legacy.id
        assert session.scalar(
            select(ContractSignatureSnapshot).where(ContractSignatureSnapshot.contract_id == legacy_id)
        ) is None

    with TestClient(app) as client:
        login(client)
        page = client.get("/operacion-comercial")
        assert page.status_code == 200
        assert "firma legacy sin snapshot V2.60.6" in page.text

    with SessionLocal() as session:
        legacy = session.get(ServiceContract, legacy_id)
        assert legacy.signature_hash == before_hash
        assert session.scalar(
            select(ContractSignatureSnapshot).where(ContractSignatureSnapshot.contract_id == legacy_id)
        ) is None


def test_v2606_recurring_charge_records_base_without_inventing_tax_total() -> None:
    reference = _unique("REC-V2606")
    with SessionLocal() as session:
        subscription = session.scalar(
            select(OrganizationSubscription).where(OrganizationSubscription.billing_cycle.in_(["Mensual", "Anual"])).order_by(OrganizationSubscription.id)
        )
        assert subscription is not None
        subscription_id = subscription.id

    with TestClient(app) as client:
        login(client)
        response = client.post(
            "/operacion-comercial/cobros/recurrente",
            data={
                "subscription_id": subscription_id,
                "period_start": "2026-09-01",
                "period_end": "2026-09-30",
                "due_date": "2026-10-05",
                "reference": reference,
                "notes": "Prueba V2.60.6",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

    with SessionLocal() as session:
        invoice = session.scalar(select(BillingInvoice).where(BillingInvoice.reference == reference))
        assert invoice is not None
        breakdown = session.scalar(select(BillingChargeBreakdown).where(BillingChargeBreakdown.invoice_id == invoice.id))
        assert breakdown is not None
        assert breakdown.charge_type == "Recurrente"
        assert breakdown.amount_semantics == INVOICE_BASE_BEFORE_TAX
        assert breakdown.net_amount == pytest.approx(invoice.amount)
        assert breakdown.tax_rate_snapshot is None
        assert breakdown.tax_amount is None
        assert breakdown.total_amount is None
        assert "no constituye factura electrónica" in invoice.notes.lower()


def test_v2606_recurring_charge_rejects_invalid_dates_and_negative_authority() -> None:
    with SessionLocal() as session:
        subscription = session.scalar(
            select(OrganizationSubscription).where(OrganizationSubscription.billing_cycle.in_(["Mensual", "Anual"])).order_by(OrganizationSubscription.id)
        )
        assert subscription is not None
        subscription_id = subscription.id
        original_custom = subscription.custom_monthly_fee

    with TestClient(app) as client:
        login(client)
        inverted = client.post(
            "/operacion-comercial/cobros/recurrente",
            data={
                "subscription_id": subscription_id,
                "period_start": "2026-10-01",
                "period_end": "2026-09-01",
                "due_date": "2026-10-05",
                "reference": _unique("REC-BAD-DATE"),
            },
            follow_redirects=False,
        )
        assert inverted.status_code == 400
        due_before_end = client.post(
            "/operacion-comercial/cobros/recurrente",
            data={
                "subscription_id": subscription_id,
                "period_start": "2026-09-01",
                "period_end": "2026-09-30",
                "due_date": "2026-09-15",
                "reference": _unique("REC-BAD-DUE"),
            },
            follow_redirects=False,
        )
        assert due_before_end.status_code == 400

    with SessionLocal() as session:
        subscription = session.get(OrganizationSubscription, subscription_id)
        subscription.custom_monthly_fee = -10
        session.commit()
    try:
        with TestClient(app) as client:
            login(client)
            negative = client.post(
                "/operacion-comercial/cobros/recurrente",
                data={
                    "subscription_id": subscription_id,
                    "period_start": "2026-11-01",
                    "period_end": "2026-11-30",
                    "due_date": "2026-12-05",
                    "reference": _unique("REC-BAD-MONEY"),
                },
                follow_redirects=False,
            )
            assert negative.status_code == 409
    finally:
        with SessionLocal() as session:
            subscription = session.get(OrganizationSubscription, subscription_id)
            subscription.custom_monthly_fee = original_custom
            session.commit()


def test_v2606_base_pending_tax_cannot_be_marked_as_paid_total() -> None:
    with SessionLocal() as session:
        invoice = session.scalar(
            select(BillingInvoice)
            .join(BillingChargeBreakdown, BillingChargeBreakdown.invoice_id == BillingInvoice.id)
            .where(BillingChargeBreakdown.amount_semantics == INVOICE_BASE_BEFORE_TAX)
            .order_by(BillingInvoice.id.desc())
        )
        if invoice is None:
            pytest.skip("Requiere el registro recurrente del contrato V2.60.6")
        action = CollectionAction(
            organization_id=invoice.organization_id,
            invoice_id=invoice.id,
            action_type="Confirmación de pago",
            channel="Correo",
            status="Pendiente",
            notes="No debe cerrar una base pendiente de impuesto",
            created_by="test@calculatuhuella.local",
        )
        session.add(action)
        session.commit()
        action_id = action.id
        invoice_id = invoice.id

    with TestClient(app) as client:
        login(client)
        response = client.post(
            f"/operacion-comercial/cartera/{action_id}/completar",
            data={"result": "Cliente informa pago", "invoice_status": "Pagada"},
            follow_redirects=False,
        )
        assert response.status_code == 409

    with SessionLocal() as session:
        action = session.get(CollectionAction, action_id)
        invoice = session.get(BillingInvoice, invoice_id)
        assert action.status == "Pendiente"
        assert invoice.status != "Pagada"


def test_v2606_activation_payment_has_authoritative_net_tax_total_breakdown() -> None:
    token = _unique("PROP-ACT-TOKEN")
    with SessionLocal() as session:
        lead = session.scalar(select(CommercialLead).order_by(CommercialLead.id))
        plan = session.scalar(select(ServicePlan).where(ServicePlan.active.is_(True)).order_by(ServicePlan.id))
        assert lead is not None and plan is not None
        implementation = 1000000.0
        recurring = 200000.0
        discount = 50000.0
        tax = 19.0
        proposal = CommercialProposal(
            lead_id=lead.id,
            plan_id=plan.id,
            reference=_unique("PROP-ACT"),
            public_token=token,
            title="Activación V2.60.6",
            company_name=_unique("Empresa Activación"),
            contact_name="Cliente Prueba",
            contact_email="cliente-v2606@example.com",
            status="Enviada",
            valid_until=date.today() + timedelta(days=30),
            billing_cycle="Anual",
            implementation_fee=implementation,
            recurring_fee=recurring,
            discount_amount=discount,
            tax_rate=tax,
            first_year_total=proposal_first_year_total(implementation, recurring, discount, tax, "Anual"),
            scope_json='["Alcance"]',
            deliverables_json='["Entregable"]',
            terms="Condiciones V2.60.6",
            contract_version="1.1",
        )
        session.add(proposal)
        session.commit()
        proposal_id = proposal.id

    with TestClient(app) as client:
        accepted = client.post(
            f"/propuesta/{token}/aceptar",
            data={"accepted_by": "Cliente Prueba", "accepted_email": "cliente-v2606@example.com", "accept_terms": "1"},
            follow_redirects=False,
        )
        assert accepted.status_code == 303
        with SessionLocal() as session:
            payment = session.scalar(select(PaymentTransaction).where(PaymentTransaction.proposal_id == proposal_id))
            assert payment is not None
            payment_token = payment.public_token
        confirmed = client.post(
            f"/pago/{payment_token}/confirmar",
            data={"payer_name": "Cliente Prueba", "payer_email": "cliente-v2606@example.com"},
            follow_redirects=False,
        )
        assert confirmed.status_code == 303

    with SessionLocal() as session:
        payment = session.scalar(select(PaymentTransaction).where(PaymentTransaction.proposal_id == proposal_id))
        assert payment is not None and payment.invoice_id is not None
        invoice = session.get(BillingInvoice, payment.invoice_id)
        breakdown = session.scalar(select(BillingChargeBreakdown).where(BillingChargeBreakdown.invoice_id == invoice.id))
        assert breakdown is not None
        assert breakdown.charge_type == "Activación"
        assert breakdown.amount_semantics == INVOICE_TOTAL_WITH_TAX
        expected_net = implementation + recurring - discount
        expected_tax = expected_net * 0.19
        assert breakdown.net_amount == pytest.approx(expected_net)
        assert breakdown.tax_rate_snapshot == pytest.approx(19.0)
        assert breakdown.tax_amount == pytest.approx(expected_tax)
        assert breakdown.total_amount == pytest.approx(payment.amount)
        assert invoice.amount == pytest.approx(payment.amount)


def test_v2606_operations_ui_names_semantics_and_tax_boundary_explicitly() -> None:
    source = TEMPLATE.read_text(encoding="utf-8")
    assert "Cartera · total conocido" in source
    assert "Base pendiente de impuesto" in source
    assert "Legacy por clasificar" in source
    assert "No se infiere neto/impuesto/total" in source
    assert "no emite facturación electrónica DIAN" in source
    assert "firma legacy sin snapshot V2.60.6" in source
    assert "snapshot {{ signature.signature_version }}" in source


def test_v2606_external_emission_requires_real_provider_identity() -> None:
    with SessionLocal() as session:
        document = session.scalar(select(BillingInvoice).order_by(BillingInvoice.id))
        if document is None:
            pytest.skip("No hay cobros en la semilla")
        from app.db.models import BillingDocumentRecord
        record = session.scalar(
            select(BillingDocumentRecord).where(BillingDocumentRecord.invoice_id == document.id).order_by(BillingDocumentRecord.id)
        )
        if record is None:
            pytest.skip("No hay documento de cobro en la semilla")
        record_id = record.id

    with TestClient(app) as client:
        login(client)
        response = client.post(
            f"/operacion-comercial/documentos/{record_id}/actualizar",
            data={
                "status": "Emitido externamente",
                "provider": "Sin integración",
                "external_number": "FE-1",
                "issued_at": date.today().isoformat(),
            },
            follow_redirects=False,
        )
        assert response.status_code == 400
