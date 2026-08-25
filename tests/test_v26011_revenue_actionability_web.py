from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.db.models import BillingInvoice, Organization, ServiceContract
from app.main import app
from app.revenue_operations import INVOICE_BASE_BEFORE_TAX


def _login(client: TestClient) -> None:
    response = client.post(
        "/login",
        data={"email": "consultor@calculatuhuella.local", "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v26011_commercial_operations_get_surfaces_action_without_mutating_contract() -> None:
    today = date.today()
    reference = "CTR-V26011-READONLY"
    with SessionLocal() as session:
        organization = session.scalar(select(Organization).order_by(Organization.id))
        assert organization is not None
        contract = ServiceContract(
            organization_id=organization.id,
            reference=reference,
            title="Contrato pendiente de firma V2.60.11",
            version="1.0",
            status="Borrador",
            start_date=today,
            end_date=today + timedelta(days=365),
            renewal_type="Anual",
            auto_renew=False,
            notice_days=30,
            contract_value=Decimal("123456.78"),
            billing_cycle="Anual",
            owner="Equipo comercial",
            terms_snapshot="Condiciones de prueba V2.60.11",
            created_by="test@calculatuhuella.local",
        )
        session.add(contract)
        session.commit()
        contract_id = contract.id
        before = {
            "status": contract.status,
            "signature_hash": contract.signature_hash,
            "contract_value": contract.contract_value,
            "updated_at": contract.updated_at,
        }

    with TestClient(app) as client:
        _login(client)
        response = client.get("/operacion-comercial")

    assert response.status_code == 200
    assert "Qué requiere atención ahora" in response.text
    assert "Completar firma contractual" in response.text
    assert reference in response.text
    assert 'id="prioridades-comerciales"' in response.text
    assert 'id="contratos"' in response.text
    assert 'id="ordenes"' in response.text
    assert 'id="cobros"' in response.text
    assert 'id="cartera"' in response.text
    assert "no crea un score de cliente" in response.text

    with SessionLocal() as session:
        contract = session.get(ServiceContract, contract_id)
        assert contract is not None
        after = {
            "status": contract.status,
            "signature_hash": contract.signature_hash,
            "contract_value": contract.contract_value,
            "updated_at": contract.updated_at,
        }
        assert after == before


def test_v26011_overdue_tax_base_stays_base_after_actionability_page_render() -> None:
    today = date.today()
    reference = "REC-V26011-TAX-BASE"
    with SessionLocal() as session:
        organization = session.scalar(select(Organization).order_by(Organization.id))
        assert organization is not None
        invoice = BillingInvoice(
            organization_id=organization.id,
            subscription_id=None,
            reference=reference,
            period_start=today - timedelta(days=35),
            period_end=today - timedelta(days=5),
            amount=Decimal("250000.00"),
            status="Pendiente",
            issued_at=today - timedelta(days=35),
            due_date=today - timedelta(days=1),
            notes="Base contractual de prueba; impuesto pendiente.",
            charge_type="Recurrente",
            amount_semantics=INVOICE_BASE_BEFORE_TAX,
            net_amount=Decimal("250000.00"),
            tax_rate_snapshot=None,
            tax_amount=None,
            total_amount=None,
            source_reference="TEST-V26011",
            classification_note="No existe autoridad tributaria para calcular total.",
        )
        session.add(invoice)
        session.commit()
        invoice_id = invoice.id

    with TestClient(app) as client:
        _login(client)
        response = client.get("/operacion-comercial")

    assert response.status_code == 200
    assert "Resolver cobro vencido con total aún no determinado" in response.text
    assert reference in response.text
    assert "Base antes de impuesto" in response.text
    assert "250.000" in response.text

    with SessionLocal() as session:
        invoice = session.get(BillingInvoice, invoice_id)
        assert invoice is not None
        assert invoice.amount_semantics == INVOICE_BASE_BEFORE_TAX
        assert invoice.amount == Decimal("250000.00")
        assert invoice.net_amount == Decimal("250000.00")
        assert invoice.tax_rate_snapshot is None
        assert invoice.tax_amount is None
        assert invoice.total_amount is None
