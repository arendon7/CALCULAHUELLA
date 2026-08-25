from __future__ import annotations

from datetime import date

import pytest
from fastapi import HTTPException

from app.db.models import BillingInvoice, CommercialProposal, PaymentTransaction
from app.payment_web import _classify_activation_invoice


def test_v2606_preexisting_activation_invoice_amount_must_match_accepted_payment() -> None:
    proposal = CommercialProposal(
        reference="PROP-V2606-INTEGRITY",
        public_token="TOKEN-V2606-INTEGRITY",
        title="Integridad activación",
        company_name="Empresa V2.60.6",
        billing_cycle="Anual",
        implementation_fee=1_000_000,
        recurring_fee=200_000,
        discount_amount=50_000,
        tax_rate=19,
        first_year_total=1_368_500,
        scope_json="[]",
        deliverables_json="[]",
        terms="Condiciones",
        contract_version="1.1",
    )
    payment = PaymentTransaction(
        public_token="PAY-TOKEN-V2606-INTEGRITY",
        amount=1_368_500,
        currency="COP",
        external_reference="PAY-PROP-V2606-INTEGRITY",
    )
    invoice = BillingInvoice(
        organization_id=1,
        reference="COBRO-PROP-V2606-INTEGRITY",
        period_start=date(2026, 8, 24),
        period_end=date(2027, 8, 24),
        amount=1_368_600,
        status="Pendiente",
        issued_at=date(2026, 8, 24),
        due_date=date(2026, 8, 24),
        notes="Registro preexistente con valor distinto.",
    )

    with pytest.raises(HTTPException) as caught:
        _classify_activation_invoice(invoice, proposal, payment)

    assert caught.value.status_code == 409
    assert "cobro existente" in str(caught.value.detail).lower()
    assert invoice.amount_semantics is None
    assert invoice.net_amount is None
    assert invoice.tax_amount is None
    assert invoice.total_amount is None


def test_v2606_matching_activation_invoice_can_be_classified_once() -> None:
    proposal = CommercialProposal(
        reference="PROP-V2606-IDEMPOTENT",
        public_token="TOKEN-V2606-IDEMPOTENT",
        title="Activación idempotente",
        company_name="Empresa V2.60.6",
        billing_cycle="Anual",
        implementation_fee=1_000_000,
        recurring_fee=200_000,
        discount_amount=50_000,
        tax_rate=19,
        first_year_total=1_368_500,
        scope_json="[]",
        deliverables_json="[]",
        terms="Condiciones",
        contract_version="1.1",
    )
    payment = PaymentTransaction(
        public_token="PAY-TOKEN-V2606-IDEMPOTENT",
        amount=1_368_500,
        currency="COP",
        external_reference="PAY-PROP-V2606-IDEMPOTENT",
    )
    invoice = BillingInvoice(
        organization_id=1,
        reference="COBRO-PROP-V2606-IDEMPOTENT",
        period_start=date(2026, 8, 24),
        period_end=date(2027, 8, 24),
        amount=1_368_500,
        status="Pendiente",
        issued_at=date(2026, 8, 24),
        due_date=date(2026, 8, 24),
        notes="Registro compatible.",
    )

    _classify_activation_invoice(invoice, proposal, payment)
    first_snapshot = (
        invoice.charge_type,
        invoice.amount_semantics,
        invoice.net_amount,
        invoice.tax_rate_snapshot,
        invoice.tax_amount,
        invoice.total_amount,
        invoice.source_reference,
    )
    _classify_activation_invoice(invoice, proposal, payment)

    assert first_snapshot == (
        invoice.charge_type,
        invoice.amount_semantics,
        invoice.net_amount,
        invoice.tax_rate_snapshot,
        invoice.tax_amount,
        invoice.total_amount,
        invoice.source_reference,
    )
    assert invoice.amount_semantics == "total_with_tax"
    assert invoice.net_amount == pytest.approx(1_150_000)
    assert invoice.tax_amount == pytest.approx(218_500)
    assert invoice.total_amount == pytest.approx(1_368_500)
