from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def login(client: TestClient, email: str = "consultor@calculatuhuella.local") -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v226_results_explain_auditable_chain_without_changing_result_semantics() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/calculos")

    assert response.status_code == 200
    for label in [
        "DE LA EVIDENCIA AL RESULTADO",
        "Dato y evidencia",
        "Factor aplicado",
        "Conversión y GWP",
        "Fórmula congelada",
        "Resultado consolidado",
    ]:
        assert label in response.text
    assert "Ver dato → factor → resultado" in response.text
    assert "HUELLA BRUTA DEL PERIODO" in response.text
    assert "Remociones, emisiones evitadas, compensaciones" in response.text


def test_v226_engine_rules_remain_available_as_progressive_detail() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/calculos")

    assert response.status_code == 200
    assert "DETALLE TÉCNICO" in response.text
    assert "Reglas del motor de cálculo" in response.text
    assert "Normaliza la unidad" in response.text
