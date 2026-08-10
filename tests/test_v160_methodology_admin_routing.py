from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.base import SessionLocal
from app.db.models import EmissionFactor, EmissionFactorVersion, Gas, UnitConversion
from app.main import app

ROOT = Path(__file__).resolve().parents[1]

METHODOLOGY_ADMIN_ROUTES = {
    ("GET", "/metodologia"),
    ("POST", "/metodologia/factores/nuevo"),
    ("POST", "/metodologia/factores/{version_id}/estado"),
    ("POST", "/metodologia/conversiones/nueva"),
}


def _login(client: TestClient, email: str = "consultor@calculatuhuella.local") -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v160_methodology_admin_has_dedicated_http_authority():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    module_source = (ROOT / "app/methodology_admin_web.py").read_text(encoding="utf-8")
    assert '@app.get("/metodologia"' not in main_source
    assert '@app.post("/metodologia/factores/nuevo"' not in main_source
    assert '@app.post("/metodologia/factores/{version_id}/estado"' not in main_source
    assert '@app.post("/metodologia/conversiones/nueva"' not in main_source
    assert "register_methodology_admin_routes(" in main_source
    assert module_source.count("@app.") == 4
    assert "normalize_factor_output" in module_source
    assert "def normalize_factor_output(" not in module_source


def test_v160_methodology_admin_route_contract_is_unique_and_complete():
    actual = []
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if path in {item[1] for item in METHODOLOGY_ADMIN_ROUTES}:
            actual.extend((method, path) for method in methods if method in {"GET", "POST"})
    assert set(actual) == METHODOLOGY_ADMIN_ROUTES
    assert len(actual) == len(METHODOLOGY_ADMIN_ROUTES)


def test_v160_methodology_page_and_factor_validation_remain_operational():
    with TestClient(app) as client:
        _login(client)
        page = client.get("/metodologia")
        assert page.status_code == 200
        with SessionLocal() as session:
            gas = session.scalar(select(Gas).order_by(Gas.id))
            assert gas is not None
            gas_id = gas.id
        invalid = client.post(
            "/metodologia/factores/nuevo",
            data={
                "name": "Factor inválido V1.6",
                "activity_type": "Prueba",
                "gas_id": gas_id,
                "value": "1",
                "input_unit": "unidad-no-autorizada",
                "output_unit": "kg gas",
                "version": "1.0",
                "source_organization": "Prueba",
                "publication_year": "2026",
            },
            follow_redirects=False,
        )
        assert invalid.status_code == 400
        assert "Unidad no autorizada" in invalid.text


def test_v160_methodology_conversion_contract_remains_dimension_safe():
    with SessionLocal() as session:
        before = list(session.scalars(select(UnitConversion)))
        existing_count = len(before)
    with TestClient(app) as client:
        _login(client)
        invalid = client.post(
            "/metodologia/conversiones/nueva",
            data={
                "from_unit": "kg",
                "to_unit": "kWh",
                "multiplier": "1",
                "source": "Prueba incompatible",
            },
            follow_redirects=False,
        )
        assert invalid.status_code == 400
    with SessionLocal() as session:
        assert len(list(session.scalars(select(UnitConversion)))) == existing_count
        assert session.scalar(select(EmissionFactor).where(EmissionFactor.name == "Factor inválido V1.6")) is None
        assert session.scalar(
            select(EmissionFactorVersion).join(EmissionFactor).where(EmissionFactor.name == "Factor inválido V1.6")
        ) is None
