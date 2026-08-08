from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import Organization, SessionLocal
from app.demo_environment import demo_environment_summary
from app.main import app
from app.product_experience import demo_story_for, navigation_for


def login(client: TestClient, email: str = "admin@calculatuhuella.local") -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_iteration11_essential_navigation_is_short_and_task_oriented() -> None:
    profiles = {
        "Cliente": {"view_inventory", "manage_activity_data", "view_results"},
        "Consultor": {
            "manage_inventory", "manage_sources", "manage_activity_data", "review",
            "view_methodology", "manage_supply_chain", "view_results",
        },
        "Administrador": {
            "manage_org", "manage_inventory", "manage_sources", "manage_activity_data",
            "review", "view_methodology", "manage_methodology_governance",
            "manage_operations", "manage_saas", "manage_portfolio", "view_results",
        },
    }
    for role, capabilities in profiles.items():
        essential = navigation_for({"role": role, "capabilities": capabilities}, "essential")
        complete = navigation_for({"role": role, "capabilities": capabilities}, "complete")
        essential_items = [item for section in essential["core"] for item in section["items"]]
        complete_items = [
            item
            for group in (complete["core"], complete["advanced"], complete["internal"])
            for section in group
            for item in section["items"]
        ]
        assert 5 <= len(essential_items) <= 9
        assert len(complete_items) > len(essential_items)
        assert essential_items[0]["label"] == "Mi trabajo"
        assert any(item["label"] == "Centro de trabajo" for item in complete_items)


def test_iteration11_five_demo_stories_have_distinct_purposes() -> None:
    names = [
        "Greenatics", "Industrias Andinas", "Café Sierra Verde",
        "Ruta Norte Logística", "Hotel Bosque Azul",
    ]
    stories = [demo_story_for(name) for name in names]
    assert all(story and story["headline"] and story["action"] for story in stories)
    assert len({story["phase"] for story in stories}) >= 4
    assert len({story["route"] for story in stories}) >= 4


def test_iteration11_dashboard_uses_progressive_disclosure_and_fast_company_switcher() -> None:
    with TestClient(app) as client:
        login(client)
        page = client.get("/dashboard")
        assert page.status_code == 200
        assert 'class="org-switcher"' in page.text
        assert 'class="demo-story' in page.text
        assert 'class="dashboard-disclosure ' in page.text
        assert "ANÁLISIS DETALLADO" in page.text


def test_iteration11_demo_portfolio_is_populated_and_stage_diverse() -> None:
    with SessionLocal() as session:
        summary = demo_environment_summary(session)
        assert summary["organization_count"] == 5
        assert summary["totals"]["activity_records"] >= 250
        assert summary["totals"]["calculations"] >= 300
        assert summary["totals"]["evidence"] >= 15
        assert len({row["sector"] for row in summary["organizations"]}) == 5
        assert len({row["current_stage"] for row in summary["organizations"]}) >= 3
        assert all(row["profile_completion"] == 100 for row in summary["organizations"])


def test_iteration11_switching_demo_company_redirects_to_its_dashboard() -> None:
    with TestClient(app) as client:
        login(client)
        with SessionLocal() as session:
            target = session.scalar(
                select(Organization).where(Organization.trade_name == "Ruta Norte Logística")
            )
            assert target is not None
        response = client.post(
            f"/portafolio/cambiar/{target.id}",
            data={"return_url": "/dashboard"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        page = client.get("/dashboard")
        assert page.status_code == 200
        assert "Ruta Norte Logística" in page.text
        assert "Flota, centros logísticos" in page.text
