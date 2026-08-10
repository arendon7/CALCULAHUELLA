from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.base import SessionLocal
from app.db.models import CommercialProposal
from app.main import app

ROOT = Path(__file__).resolve().parents[1]

COMMERCIAL_ROUTES = {
    ("GET", "/comercial"),
    ("POST", "/comercial/leads/{lead_id}/estado"),
    ("POST", "/comercial/propuestas/nueva"),
    ("POST", "/comercial/propuestas/{proposal_id}/enviar"),
    ("GET", "/propuesta/{token}"),
}


def _login(client: TestClient) -> None:
    response = client.post(
        "/login",
        data={"email": "admin@calculatuhuella.local", "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v170_commercial_proposals_have_dedicated_http_authority():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    module_source = (ROOT / "app/commercial_web.py").read_text(encoding="utf-8")
    assert '@app.get("/comercial"' not in main_source
    assert '@app.post("/comercial/leads/' not in main_source
    assert '@app.post("/comercial/propuestas/' not in main_source
    assert '@app.get("/propuesta/{token}"' not in main_source
    # Acceptance/payment intentionally stay outside this cut.
    assert '@app.post("/propuesta/{token}/aceptar"' in main_source
    assert "register_commercial_routes(" in main_source
    assert module_source.count("@app.") == 5
    assert "PaymentTransaction" in module_source
    assert '@app.post("/propuesta/{token}/aceptar"' not in module_source


def test_v170_commercial_route_contract_is_unique_and_complete():
    actual = []
    relevant = {path for _, path in COMMERCIAL_ROUTES}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if path in relevant:
            actual.extend((method, path) for method in methods if method in {"GET", "POST"})
    assert set(actual) == COMMERCIAL_ROUTES
    assert len(actual) == len(COMMERCIAL_ROUTES)


def test_v170_commercial_center_and_public_proposal_remain_available():
    with SessionLocal() as session:
        proposal = session.scalar(select(CommercialProposal).order_by(CommercialProposal.id))
        assert proposal is not None
        token = proposal.public_token
    with TestClient(app) as client:
        _login(client)
        assert client.get("/comercial").status_code == 200
        public = client.get(f"/propuesta/{token}")
        assert public.status_code == 200
        assert proposal.reference in public.text
