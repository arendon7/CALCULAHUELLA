from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace as NS

from app.revenue_actionability import build_revenue_action_queue, summarize_revenue_actions
from app.revenue_operations import INVOICE_BASE_BEFORE_TAX, INVOICE_TOTAL_WITH_TAX


def _org_names() -> dict[int, str]:
    return {1: "Acme SAS", 2: "Beta SAS"}


def test_v26011_accepted_proposal_without_contract_becomes_explicit_handoff() -> None:
    today = date(2026, 8, 25)
    proposal = NS(id=91, status="Aceptada", organization_id=1, reference="PROP-91", company_name="Acme SAS")

    actions = build_revenue_action_queue(
        contracts=[],
        orders=[],
        invoices=[],
        proposals=[proposal],
        collection_actions=[],
        breakdown_by_invoice={},
        organization_names=_org_names(),
        today=today,
    )

    assert [item.key for item in actions] == ["proposal:91:contract"]
    assert actions[0].priority == "high"
    assert actions[0].title == "Formalizar propuesta aceptada"
    assert actions[0].href == "#contratos"
    assert actions[0].due_date is None


def test_v26011_existing_contract_suppresses_duplicate_proposal_handoff() -> None:
    today = date(2026, 8, 25)
    proposal = NS(id=91, status="Aceptada", organization_id=1, reference="PROP-91", company_name="Acme SAS")
    contract = NS(
        id=7,
        proposal_id=91,
        organization_id=1,
        reference="CTR-7",
        status="Borrador",
        signature_hash="",
        end_date=None,
        notice_days=30,
        renewal_type="Anual",
    )

    actions = build_revenue_action_queue(
        contracts=[contract],
        orders=[],
        invoices=[],
        proposals=[proposal],
        collection_actions=[],
        breakdown_by_invoice={},
        organization_names=_org_names(),
        today=today,
    )

    assert "proposal:91:contract" not in {item.key for item in actions}
    assert "contract:7:signature" in {item.key for item in actions}


def test_v26011_contract_deadlines_use_persisted_dates_and_notice_window() -> None:
    today = date(2026, 8, 25)
    expired = NS(
        id=1,
        proposal_id=None,
        organization_id=1,
        reference="CTR-OLD",
        status="Vigente",
        signature_hash="hash",
        end_date=today - timedelta(days=1),
        notice_days=30,
        renewal_type="Anual",
    )
    renewable = NS(
        id=2,
        proposal_id=None,
        organization_id=1,
        reference="CTR-RENEW",
        status="Vigente",
        signature_hash="hash",
        end_date=today + timedelta(days=20),
        notice_days=30,
        renewal_type="Anual",
    )
    nonrenewable = NS(
        id=3,
        proposal_id=None,
        organization_id=2,
        reference="CTR-CLOSE",
        status="Vigente",
        signature_hash="hash",
        end_date=today + timedelta(days=90),
        notice_days=30,
        renewal_type="No renovable",
    )

    actions = build_revenue_action_queue(
        contracts=[nonrenewable, renewable, expired],
        orders=[],
        invoices=[],
        proposals=[],
        collection_actions=[],
        breakdown_by_invoice={},
        organization_names=_org_names(),
        today=today,
    )

    assert actions[0].key == "contract:1:expired-status"
    assert actions[0].priority == "critical"
    by_key = {item.key: item for item in actions}
    assert by_key["contract:2:notice-window"].priority == "high"
    assert by_key["contract:2:notice-window"].due_date == renewable.end_date
    assert by_key["contract:3:upcoming-end"].priority == "medium"
    assert by_key["contract:3:upcoming-end"].title == "Preparar cierre contractual"


def test_v26011_service_orders_surface_blockage_acceptance_and_slippage() -> None:
    today = date(2026, 8, 25)
    orders = [
        NS(id=1, organization_id=1, reference="OS-1", status="Bloqueada", planned_start=today, planned_end=today + timedelta(days=4)),
        NS(id=2, organization_id=1, reference="OS-2", status="Entregada", planned_start=today - timedelta(days=8), planned_end=today - timedelta(days=1)),
        NS(id=3, organization_id=2, reference="OS-3", status="Planeada", planned_start=today - timedelta(days=2), planned_end=None),
        NS(id=4, organization_id=2, reference="OS-4", status="En ejecución", planned_start=today - timedelta(days=10), planned_end=today - timedelta(days=1)),
    ]

    actions = build_revenue_action_queue(
        contracts=[],
        orders=orders,
        invoices=[],
        proposals=[],
        collection_actions=[],
        breakdown_by_invoice={},
        organization_names=_org_names(),
        today=today,
    )

    by_key = {item.key: item for item in actions}
    assert by_key["order:1:blocked"].priority == "high"
    assert by_key["order:2:acceptance"].priority == "medium"
    assert by_key["order:3:late-start"].priority == "high"
    assert by_key["order:4:late-end"].priority == "high"


def test_v26011_overdue_invoice_prefers_existing_collection_action_without_duplicate() -> None:
    today = date(2026, 8, 25)
    invoice = NS(
        id=40,
        organization_id=1,
        reference="INV-40",
        status="Pendiente",
        due_date=today - timedelta(days=3),
        amount=Decimal("119.00"),
        amount_semantics=INVOICE_TOTAL_WITH_TAX,
        total_amount=Decimal("119.00"),
        net_amount=Decimal("100.00"),
    )
    breakdown = NS(
        amount_semantics=INVOICE_TOTAL_WITH_TAX,
        total_amount=Decimal("119.00"),
        net_amount=Decimal("100.00"),
    )
    collection = NS(
        id=8,
        invoice_id=40,
        organization_id=1,
        status="Pendiente",
        due_at=today - timedelta(days=1),
        action_type="Recordatorio",
        channel="Correo",
        invoice=invoice,
    )

    actions = build_revenue_action_queue(
        contracts=[],
        orders=[],
        invoices=[invoice],
        proposals=[],
        collection_actions=[collection],
        breakdown_by_invoice={40: breakdown},
        organization_names=_org_names(),
        today=today,
    )

    assert len(actions) == 1
    action = actions[0]
    assert action.key == "invoice:40:collection"
    assert action.priority == "critical"
    assert action.href == "#cartera"
    assert action.amount == Decimal("119.00")
    assert action.amount_label == "Total conocido"


def test_v26011_invoice_semantics_never_invent_tax_or_reclassify_legacy() -> None:
    today = date(2026, 8, 25)
    tax_base = NS(
        id=1,
        organization_id=1,
        reference="REC-BASE",
        status="Pendiente",
        due_date=today + timedelta(days=20),
        amount=Decimal("100.00"),
        amount_semantics=INVOICE_BASE_BEFORE_TAX,
        net_amount=Decimal("100.00"),
        total_amount=None,
    )
    tax_breakdown = NS(
        amount_semantics=INVOICE_BASE_BEFORE_TAX,
        net_amount=Decimal("100.00"),
        total_amount=None,
    )
    legacy = NS(
        id=2,
        organization_id=2,
        reference="INV-LEGACY",
        status="Pendiente",
        due_date=today + timedelta(days=30),
        amount=Decimal("77.77"),
        amount_semantics=None,
        net_amount=None,
        total_amount=None,
    )

    actions = build_revenue_action_queue(
        contracts=[],
        orders=[],
        invoices=[tax_base, legacy],
        proposals=[],
        collection_actions=[],
        breakdown_by_invoice={1: tax_breakdown},
        organization_names=_org_names(),
        today=today,
    )

    by_key = {item.key: item for item in actions}
    tax_action = by_key["invoice:1:tax-pending"]
    legacy_action = by_key["invoice:2:legacy"]
    assert tax_action.amount == Decimal("100.00")
    assert tax_action.amount_label == "Base antes de impuesto"
    assert "no inventa" not in tax_action.detail.lower()  # language describes the boundary, not a made-up result
    assert legacy_action.amount == Decimal("77.77")
    assert legacy_action.amount_label == "Importe legacy sin clasificar"
    assert legacy_action.priority == "high"


def test_v26011_due_collection_action_is_rule_based_and_summarized() -> None:
    today = date(2026, 8, 25)
    invoice = NS(id=77, reference="INV-77")
    due_today = NS(
        id=10,
        invoice_id=77,
        organization_id=1,
        status="Pendiente",
        due_at=today,
        action_type="Confirmación de recepción",
        channel="Teléfono",
        invoice=invoice,
    )
    overdue = NS(
        id=11,
        invoice_id=78,
        organization_id=2,
        status="Pendiente",
        due_at=today - timedelta(days=2),
        action_type="Escalamiento",
        channel="Reunión",
        invoice=NS(id=78, reference="INV-78"),
    )

    actions = build_revenue_action_queue(
        contracts=[],
        orders=[],
        invoices=[],
        proposals=[],
        collection_actions=[due_today, overdue],
        breakdown_by_invoice={},
        organization_names=_org_names(),
        today=today,
    )

    assert actions[0].key == "collection:11:due"
    assert actions[0].priority == "critical"
    assert actions[1].key == "collection:10:due"
    assert actions[1].priority == "high"
    assert summarize_revenue_actions(actions) == {"total": 2, "critical": 1, "high": 1, "medium": 0}


def test_v26011_projection_does_not_mutate_authoritative_objects() -> None:
    today = date(2026, 8, 25)
    contract = NS(
        id=9,
        proposal_id=None,
        organization_id=1,
        reference="CTR-9",
        status="Borrador",
        signature_hash="",
        end_date=None,
        notice_days=30,
        renewal_type="Anual",
    )
    before = vars(contract).copy()

    build_revenue_action_queue(
        contracts=[contract],
        orders=[],
        invoices=[],
        proposals=[],
        collection_actions=[],
        breakdown_by_invoice={},
        organization_names=_org_names(),
        today=today,
    )

    assert vars(contract) == before
