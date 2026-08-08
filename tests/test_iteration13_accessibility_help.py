from __future__ import annotations

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from app.main import app


def login(client: TestClient, email: str = "admin@calculatuhuella.local") -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def soup_for(client: TestClient, path: str) -> BeautifulSoup:
    response = client.get(path)
    assert response.status_code == 200
    return BeautifulSoup(response.text, "lxml")


def test_iteration13_base_has_landmarks_skip_links_and_live_regions() -> None:
    with TestClient(app) as client:
        login(client)
        soup = soup_for(client, "/dashboard")
        assert soup.html["lang"] == "es-CO"
        assert [link.get("href") for link in soup.select(".skip-link")] == [
            "#contenido-aplicacion",
            "#navegacion-principal",
        ]
        assert soup.select_one("aside[aria-label='Navegación de la aplicación']")
        assert soup.select_one("main#aplicacion[tabindex='-1']")
        assert soup.select_one("#live-region[aria-live='polite']")
        assert soup.select_one("#form-error-summary[role='alert']")

        # Dashboard is now a secondary summary and is intentionally absent from
        # the essential menu. Verify aria-current on the actual primary entry.
        work_soup = soup_for(client, "/mi-trabajo")
        current = work_soup.select_one(".nav-item[aria-current='page']")
        assert current is not None
        assert "Mi trabajo" in current.get_text(" ", strip=True)


def test_iteration13_context_help_and_tour_are_reopenable_accessible_dialogs() -> None:
    with TestClient(app) as client:
        login(client, "cliente@calculatuhuella.local")
        soup = soup_for(client, "/dashboard")
        help_dialog = soup.select_one("dialog#contextHelpDialog")
        tour_dialog = soup.select_one("dialog#welcomeTourDialog")
        assert help_dialog and help_dialog.get("aria-labelledby") == "context-help-title"
        assert tour_dialog and tour_dialog.get("aria-labelledby") == "tour-title"
        assert "cliente" in tour_dialog.get("data-tour-storage-key", "")
        assert len(tour_dialog.select("[data-tour-step]")) == 4
        assert soup.select_one("button[data-open-context-help][aria-label]")
        assert soup.select_one("button[data-open-tour][aria-label]")
        assert "Tu enfoque como Cliente" in help_dialog.get_text(" ", strip=True)


def test_iteration13_secondary_loading_actions_are_grouped() -> None:
    with TestClient(app) as client:
        login(client)
        information = soup_for(client, "/informacion")
        capture = soup_for(client, "/captura-guiada")
        assert information.select_one("details.head-action-menu > summary")
        assert capture.select_one("details.head-action-menu > summary")
        assert "Registrar un dato" in information.get_text(" ", strip=True)
        assert "Ver datos y evidencias" in capture.get_text(" ", strip=True)
        assert "Consultar guía" not in soup_for(client, "/dashboard").get_text(" ", strip=True)


def test_iteration13_key_pages_have_unique_ids_and_named_buttons() -> None:
    with TestClient(app) as client:
        login(client)
        for path in ("/dashboard", "/informacion", "/captura-guiada", "/recorrido-inventario"):
            soup = soup_for(client, path)
            ids = [node["id"] for node in soup.select("[id]")]
            assert len(ids) == len(set(ids)), path
            for button in soup.select("button"):
                name = button.get("aria-label") or button.get_text(" ", strip=True) or button.get("title")
                assert name, f"Unnamed button on {path}: {button}"


def test_iteration13_assets_include_accessibility_behaviors() -> None:
    with TestClient(app) as client:
        entry = client.get("/static/css/app.css")
        canonical = client.get("/static/css/app-canonical-v1.css")
        overlay = client.get("/static/css/v1.4.css")
        js = client.get("/static/js/app.js")
        assert all(response.status_code == 200 for response in (entry, canonical, overlay, js))
        assert '@import url("./app-canonical-v1.css")' in entry.text
        assert '@import url("./v1.4.css")' in entry.text
        effective_css = "\n".join((entry.text, canonical.text, overlay.text))
        for token in (":focus-visible", "prefers-reduced-motion", ".access-dialog", "[aria-invalid=\"true\"]"):
            assert token in effective_css
        for token in (
            "initializeWelcomeTour",
            "initializeFormAccessibility",
            "initializeTableAccessibility",
            "openAccessibleDialog",
        ):
            assert token in js.text
