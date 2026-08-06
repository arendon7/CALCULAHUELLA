from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.architecture import domain_architecture_summary, persistence_architecture_summary
from app.database import Base, ENGINE, Facility, Inventory, Organization, ReportArtifact, SessionLocal, init_db
from app.db.models.core import Organization as DomainOrganization
from app.db.models.inventory import Inventory as DomainInventory
from app.main import app
from app.repositories.organizations import get_facility, get_organization
from app.repositories.reports import get_report_artifact


@pytest.fixture(autouse=True)
def fresh_database_v037():
    # La base semilla aislada se restaura desde tests/conftest.py.
    yield


def login(client: TestClient, email: str = "admin@calculatuhuella.local") -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v037_health_and_persistence_summary():
    with TestClient(app) as client:
        assert client.get("/api/health").json()["version"] == "1.0.0"
        login(client)
        response = client.get("/api/arquitectura/resumen")
        assert response.status_code == 200
        summary = response.json()
    assert summary["architecture_split_ok"] is True
    assert summary["persistence"]["split_ok"] is True
    assert summary["persistence"]["database_lines"] < 2200
    assert summary["persistence"]["model_module_count"] == 12
    assert summary["persistence"]["model_class_count"] == 120
    assert summary["persistence"]["repository_count"] == 5
    assert summary["persistence"]["service_count"] == 5


def test_v037_database_is_compatibility_facade_without_orm_classes():
    project_dir = Path(__file__).resolve().parents[1]
    database_path = project_dir / "app" / "database.py"
    tree = ast.parse(database_path.read_text(encoding="utf-8"))
    class_names = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
    assert class_names == []
    assert Organization is DomainOrganization
    assert Inventory is DomainInventory
    assert len(Base.metadata.tables) == 120


def test_v037_model_modules_are_complete_and_importable():
    project_dir = Path(__file__).resolve().parents[1]
    persistence = persistence_architecture_summary(project_dir)
    assert persistence["split_ok"] is True
    assert sum(item["class_count"] for item in persistence["model_modules"]) == 120
    assert all(item["exists"] and item["class_count"] > 0 for item in persistence["model_modules"])


def test_v037_services_preserve_routes_and_tenant_scoping():
    with TestClient(app) as client:
        login(client)
        response = client.post(
            "/sedes/nueva",
            data={
                "name": "Sede repositorio V037",
                "facility_type": "Operativa",
                "city": "Medellín",
                "address": "Calle 37",
                "employees": "8",
                "ownership_percentage": "100",
                "operational_control": "on",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        response = client.post(
            "/inventarios/nuevo",
            data={
                "name": "Inventario persistencia 2028",
                "start_date": "2028-01-01",
                "end_date": "2028-12-31",
                "objective": "Validar repositorios y servicios",
                "base_year": "2028",
                "methodology": "GHG Protocol + ISO 14064-1",
                "methodology_version": "V0.45",
                "gwp_version": "IPCC AR6",
                "consolidation_approach": "Control operacional",
                "materiality_threshold": "5",
                "notes": "Prueba V0.45",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
    with SessionLocal() as session:
        org = session.scalar(select(Organization).order_by(Organization.id))
        facility = session.scalar(select(Facility).where(Facility.name == "Sede repositorio V037"))
        inventory = session.scalar(select(Inventory).where(Inventory.name == "Inventario persistencia 2028"))
        assert org is not None and facility is not None and inventory is not None
        assert inventory.version == "1.0"
        assert get_organization(session, org.id) is org
        assert get_facility(session, org.id, facility.id) is facility
        assert get_facility(session, org.id + 999, facility.id) is None


def test_v037_report_repository_rejects_cross_organization_access():
    with SessionLocal() as session:
        inventory = session.scalar(select(Inventory).order_by(Inventory.id))
        assert inventory is not None
        artifact = ReportArtifact(
            inventory_id=inventory.id,
            report_type="Prueba",
            file_name="prueba.pdf",
            stored_name="reports/prueba.pdf",
            file_size=1,
            sha256="0" * 64,
            version="0.37",
            status="Borrador",
            generated_by="admin@calculatuhuella.local",
        )
        session.add(artifact)
        session.commit()
        assert get_report_artifact(session, inventory.organization_id, artifact.id) is not None
        assert get_report_artifact(session, inventory.organization_id + 999, artifact.id) is None


def test_v037_route_architecture_remains_unchanged():
    project_dir = Path(__file__).resolve().parents[1]
    summary = domain_architecture_summary(app, project_dir)
    assert summary["route_parity_ok"] is True
    assert summary["duplicate_paths"] == []
    assert summary["domain_count"] == 15
    assert summary["owned_route_count"] >= 100
