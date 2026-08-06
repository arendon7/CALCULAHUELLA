from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.architecture import domain_architecture_summary
from app.database import Base, ENGINE, Inventory, SessionLocal, init_db
from app.main import app


@pytest.fixture(autouse=True)
def fresh_database_v035():
    # La base semilla aislada se restaura desde tests/conftest.py.
    yield


def login(client: TestClient, email: str = "admin@calculatuhuella.local") -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v035_health_and_domain_route_parity():
    with TestClient(app) as client:
        assert client.get("/api/health").json()["version"] == "1.0.0"
        login(client)
        response = client.get("/api/arquitectura/resumen")
        assert response.status_code == 200
        summary = response.json()
    assert summary["route_parity_ok"] is True
    assert summary["duplicate_paths"] == []
    assert summary["domain_count"] >= 4
    assert summary["owned_route_count"] >= 24
    assert summary["main_lines"] < 5500


def test_v035_routes_are_owned_by_explicit_domain_modules():
    project_dir = Path(__file__).resolve().parents[1]
    summary = domain_architecture_summary(app, project_dir)
    expected = {
        "users": 8,
        "inventories": 17,
        "reports": 6,
        "operations": 15,
        "service_operations": 2,
    }
    actual = {item["code"]: item["route_count"] for item in summary["domains"]}
    assert {key: actual[key] for key in expected} == expected
    main_source = (project_dir / "app" / "main.py").read_text(encoding="utf-8")
    assert '@app.get("/usuarios"' not in main_source
    assert '@app.get("/inventarios"' not in main_source
    assert '@app.get("/reportes"' not in main_source
    assert "register_user_routes(" in main_source
    assert "register_inventory_routes(" in main_source
    assert "register_report_routes(" in main_source


def test_v035_extracted_user_inventory_and_report_pages_load():
    with TestClient(app) as client:
        login(client)
        for path in ("/usuarios", "/inventarios", "/inventarios/1", "/reportes", "/consolidacion"):
            response = client.get(path)
            assert response.status_code == 200, path
            assert "Calcula tu Huella" in response.text
        assert "Propiedad explícita de rutas" in client.get("/consolidacion").text


def test_v035_new_inventory_records_current_application_version():
    with TestClient(app) as client:
        login(client, "consultor@calculatuhuella.local")
        response = client.post(
            "/inventarios/nuevo",
            data={
                "name": "Inventario modular 2027",
                "start_date": "2027-01-01",
                "end_date": "2027-12-31",
                "objective": "Validar arquitectura por dominios",
                "base_year": "2027",
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
        inventory = session.scalar(select(Inventory).where(Inventory.name == "Inventario modular 2027"))
        assert inventory is not None
        assert inventory.version == "1.0"


def test_v035_mac_cleanup_preserves_current_release_zip(tmp_path: Path):
    import os
    import subprocess

    home = tmp_path / "home"
    downloads = home / "Downloads"
    downloads.mkdir(parents=True)
    current_zip = downloads / "calcula_tu_huella_v1_0_0_preparacion_productiva_dual_mac_windows.zip"
    old_zip = downloads / "calcula_tu_huella_v0_34_completa_mac.zip"
    current_zip.write_bytes(b"current")
    old_zip.write_bytes(b"old")
    project_dir = Path(__file__).resolve().parents[1]
    script = f'''
set -e
export HOME="{home}"
export CTH_INSTALL_ROOT="{home / 'Library/Application Support/CalculaTuHuella'}"
export CTH_LEGACY_SEARCH_ROOTS="{downloads}"
export CTH_TRASH_DIR="{home / '.Trash'}"
export CTH_DELETE_OLD_VERSIONS=1
source "{project_dir / 'scripts/mac_lifecycle_common.sh'}"
cth_init_install_paths "{project_dir}"
cth_mkdirs
cth_cleanup_legacy_versions
'''
    subprocess.run(["bash", "-lc", script], check=True, env={**os.environ, "HOME": str(home)})
    assert current_zip.exists()
    assert not old_zip.exists()
    assert any((home / ".Trash").glob("calcula_tu_huella_v0_34_completa_mac.zip_*"))
