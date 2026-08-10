from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.payment_web import PaymentWebhookPayload

ROOT = Path(__file__).resolve().parents[1]

PAYMENT_ROUTES = {
    ("POST", "/propuesta/{token}/aceptar"),
    ("POST", "/propuesta/{token}/rechazar"),
    ("GET", "/pago/{token}"),
    ("POST", "/pago/{token}/confirmar"),
    ("POST", "/api/pagos/webhook"),
}


def test_v170_payments_have_dedicated_http_authority():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    module_source = (ROOT / "app/payment_web.py").read_text(encoding="utf-8")
    for marker in (
        '@app.post("/propuesta/{token}/aceptar"',
        '@app.post("/propuesta/{token}/rechazar"',
        '@app.get("/pago/{token}"',
        '@app.post("/pago/{token}/confirmar"',
        '@app.post("/api/pagos/webhook"',
    ):
        assert marker not in main_source
    assert "register_payment_routes(app, templates)" in main_source
    assert module_source.count("@app.") == 5
    assert module_source.index("class PaymentWebhookPayload") < module_source.index("def register_payment_routes")
    assert "hmac.compare_digest" in module_source
    assert "CustomerOnboardingItem" in module_source


def test_v170_payment_payload_is_module_level_and_validates_json():
    payload = PaymentWebhookPayload(
        external_reference="PAY-TEST-001",
        status="paid",
        amount=1000,
        payer_email="payer@example.com",
    )
    assert payload.external_reference == "PAY-TEST-001"
    assert payload.amount == 1000


def test_v170_payment_route_contract_is_unique_and_complete():
    actual = []
    relevant = {path for _, path in PAYMENT_ROUTES}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if path in relevant:
            actual.extend((method, path) for method in methods if method in {"GET", "POST"})
    assert set(actual) == PAYMENT_ROUTES
    assert len(actual) == len(PAYMENT_ROUTES)


def test_v170_payment_webhook_rejects_unsigned_requests_before_lookup():
    with TestClient(app) as client:
        response = client.post(
            "/api/pagos/webhook",
            json={
                "external_reference": "PAY-NOT-SIGNED",
                "status": "paid",
                "amount": 1000,
                "payer_email": "payer@example.com",
            },
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Firma de pago inválida"
