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
    assert response.status_code == 200, path
    return BeautifulSoup(response.text, "lxml")


def test_iteration14_global_plain_language_dictionary_is_accessible() -> None:
    with TestClient(app) as client:
        login(client)
        soup = soup_for(client, "/dashboard")
        button = soup.select_one("button[data-open-glossary][aria-label]")
        dialog = soup.select_one("dialog#plainLanguageDialog[aria-labelledby='plain-language-title']")
        assert button and dialog
        assert dialog.select_one("input[data-glossary-search][type='search']")
        assert dialog.select_one("[data-glossary-status][aria-live='polite']")
        assert len(dialog.select("[data-glossary-item]")) == 10
        text = dialog.get_text(" ", strip=True)
        for term in ("CO₂ equivalente", "Materialidad", "Incertidumbre", "Alcance 1, 2 y 3"):
            assert term in text


def test_iteration14_guided_capture_prioritizes_essential_fields() -> None:
    with TestClient(app) as client:
        login(client, "cliente@calculatuhuella.local")
        soup = soup_for(client, "/captura-guiada")
        form = soup.select_one("form[data-guided-capture-form][data-assist-form]")
        assert form
        assert len(form.select("fieldset.assisted-fieldset")) == 2
        advanced = form.select_one("details.advanced-form-section")
        assert advanced and not advanced.has_attr("open")
        assert advanced.select_one("input[name='uncertainty_percentage']")
        preview = form.select_one("[data-capture-preview][role='status'][aria-live='polite']")
        assert preview
        for control_id in ("capture-period-start", "capture-period-end", "capture-value", "capture-unit", "capture-origin"):
            control = form.select_one(f"#{control_id}")
            assert control and control.get("aria-describedby")
        assert "Completa primero cuatro decisiones" in form.get_text(" ", strip=True)


def test_iteration14_source_configuration_uses_plain_language_groups() -> None:
    with TestClient(app) as client:
        login(client)
        sources = soup_for(client, "/inventarios/1/fuentes")
        source_link = next((a.get("href") for a in sources.select("a[href^='/fuentes/']") if a.get("href", "").count("/") == 2), None)
        assert source_link
        soup = soup_for(client, source_link)
        form = soup.select_one("form.source-config-form[data-assist-form][data-guard-unsaved]")
        assert form
        assert form.select_one("fieldset.assisted-fieldset")
        assert form.select_one("details.advanced-form-section select[name='materiality']")
        assert form.select_one("#source-scope[aria-describedby='source-scope-help']")
        text = form.get_text(" ", strip=True)
        assert "Importancia para el inventario" in text
        assert "Alcance 1: emisiones directas" in text


def test_iteration14_assets_include_assistance_and_screen_reader_behaviors() -> None:
    with TestClient(app) as client:
        css = client.get("/static/css/app.css")
        js = client.get("/static/js/app.js")
        assert css.status_code == 200 and js.status_code == 200
        for token in (".assisted-fieldset", ".plain-glossary", ".capture-live-summary", ".advanced-form-section"):
            assert token in css.text
        for token in (
            "initializeGlossarySearch",
            "initializeFieldDescriptions",
            "initializeCapturePreview",
            "data-error-target",
        ):
            assert token in js.text


def test_iteration14_key_role_entry_points_remain_available() -> None:
    role_paths = {
        "cliente@calculatuhuella.local": ("/dashboard", "/captura-guiada"),
        "consultor@calculatuhuella.local": ("/dashboard", "/recorrido-inventario"),
        "revisor@calculatuhuella.local": ("/dashboard", "/control"),
        "verificador@calculatuhuella.local": ("/dashboard", "/verificacion"),
        "admin@calculatuhuella.local": ("/dashboard", "/portafolio"),
    }
    for email, paths in role_paths.items():
        with TestClient(app) as client:
            login(client, email)
            for path in paths:
                response = client.get(path, follow_redirects=False)
                assert response.status_code in (200, 303), (email, path, response.status_code)
