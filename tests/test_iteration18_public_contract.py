from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import CommercialLead, SessionLocal
from app.main import app

pytestmark = pytest.mark.smoke


def test_iteration18_public_v14_contract_and_diagnostic_flow() -> None:
    """Keep the public value proposition current while protecting the diagnostic handoff."""
    email = "diagnostico-v14@prospecto.test"
    with TestClient(app) as client:
        home = client.get("/")
        assert home.status_code == 200
        assert "De datos dispersos a una huella de carbono" in home.text
        assert "puedes explicar." in home.text
        assert "Medición, trazabilidad y gestión de carbono" in home.text
        assert "Empezar diagnóstico" in home.text
        assert 'href="/diagnostico"' in home.text

        response = client.post(
            "/diagnostico",
            data={
                "company_name": "Empresa Prospecto V1.4 S.A.S.",
                "contact_name": "Juliana Pérez",
                "email": email,
                "phone": "3000000000",
                "sector": "Manufactura",
                "city": "Medellín",
                "employees_band": "51 a 200",
                "facilities_count": "4",
                "has_previous_inventory": "on",
                "desired_scopes": "Alcances 1, 2 y 3 priorizado",
                "objective": "Preparación para verificación",
                "urgency": "Alta",
                "notes": "Prueba del contrato público V1.4",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"].startswith("/diagnostico/gracias/")

    with SessionLocal() as session:
        lead = session.scalar(select(CommercialLead).where(CommercialLead.email == email))
        assert lead is not None
        assert lead.complexity_score >= 10
        assert lead.recommended_plan_code in {"EMPRESARIAL", "CORPORATIVO"}
