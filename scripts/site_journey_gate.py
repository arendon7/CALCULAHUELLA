from __future__ import annotations

import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get("SITE_PREVIEW_BASE_URL", "http://127.0.0.1:8780").rstrip("/")
ARTIFACT_DIR = Path(os.environ.get("SITE_PREVIEW_ARTIFACT_DIR", "site-preview-artifacts")).resolve()


def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page.goto(BASE_URL, wait_until="domcontentloaded")
        page.locator("h1").wait_for(state="visible")
        page.wait_for_timeout(350)

        year = page.locator("#primer-ano")
        if not year.is_visible():
            raise AssertionError("Primer año: sección ausente")
        if year.locator(".year-timeline article").count() != 4:
            raise AssertionError("Primer año: la secuencia debe conservar 4 etapas")
        route_buttons = year.locator("[data-year-route]")
        if route_buttons.count() != 3:
            raise AssertionError("Primer año: se esperaban 3 profundidades comerciales")

        page.locator('select[name="sector"]').select_option("servicios")
        page.locator('input[name="sedes"]').fill("1")
        page.locator('select[name="primera"]').select_option("si")
        page.locator('select[name="datos"]').select_option("alta")
        page.locator('select[name="objetivo"]').select_option("medir")
        page.locator('[data-diagnostic-form] button[type="submit"]').click()

        route = page.locator('[data-result-route]').inner_text().strip()
        price = page.locator('[data-result-price]').inner_text().strip()
        reasons = page.locator('[data-result-why] li')
        if route != "Huella Esencial":
            raise AssertionError(f"Diagnóstico enriquecido: ruta inesperada {route!r}")
        if "$1.300.000 COP / año" not in price:
            raise AssertionError(f"Diagnóstico enriquecido: precio inesperado {price!r}")
        if reasons.count() < 3:
            raise AssertionError(f"Diagnóstico enriquecido: faltan razones, hay {reasons.count()}")
        if page.locator('[data-year-title]').inner_text().strip() != "Huella Esencial":
            raise AssertionError("Diagnóstico no sincronizó el plan de primer año")
        selected = page.locator('[data-year-route="Huella Esencial"]').get_attribute("aria-selected")
        if selected != "true":
            raise AssertionError("Primer año: Huella Esencial no quedó seleccionada por el diagnóstico")
        stored = page.evaluate("localStorage.getItem('cthDiagnostic')")
        if not stored or json.loads(stored).get("route") != "Huella Esencial":
            raise AssertionError(f"Diagnóstico: persistencia inválida {stored!r}")

        page.reload(wait_until="domcontentloaded")
        page.locator("h1").wait_for(state="visible")
        page.wait_for_timeout(350)
        if page.locator('[data-result-route]').inner_text().strip() != "Huella Esencial":
            raise AssertionError("Diagnóstico: el resultado no se restauró al recargar")
        if page.locator('select[name="sector"]').input_value() != "servicios":
            raise AssertionError("Diagnóstico: el formulario no restauró sus respuestas")
        if page.locator('[data-result-why] li').count() < 3:
            raise AssertionError("Diagnóstico: la explicación no se reconstruyó al recargar")

        essential = page.locator('[data-year-route="Huella Esencial"]')
        essential.focus()
        page.keyboard.press("ArrowRight")
        if page.locator('[data-year-title]').inner_text().strip() != "Gestión de Carbono":
            raise AssertionError("Primer año: ArrowRight no cambió a Gestión de Carbono")
        if "$3.300.000 COP / año" not in page.locator('[data-year-price]').inner_text():
            raise AssertionError("Primer año: precio de Gestión de Carbono no sincronizado")
        page.keyboard.press("ArrowRight")
        if page.locator('[data-year-title]').inner_text().strip() != "Gestión Avanzada":
            raise AssertionError("Primer año: segundo ArrowRight no cambió a Gestión Avanzada")
        if "revisión específica" not in page.locator('[data-year-output]').inner_text().lower():
            raise AssertionError("Primer año: Gestión Avanzada perdió profundidad documental")

        close_nav = page.locator('[data-preview-view="cierre"]')
        if close_nav.count() != 1:
            raise AssertionError("Preview: falta módulo Cierre")
        close_nav.click()
        close_panel = page.locator('[data-preview-panel="cierre"]')
        if not close_panel.is_visible():
            raise AssertionError("Preview: Cierre no se volvió visible")
        if close_panel.locator('.preview-close-gates article').count() != 5:
            raise AssertionError("Preview: Cierre debe mostrar 5 condiciones")
        close_text = close_panel.inner_text().lower()
        if "no listo" not in close_text or "no se bloquea" not in close_text:
            raise AssertionError("Preview: Cierre perdió su regla fail-closed")
        close_button = close_panel.locator('button[disabled]')
        if close_button.count() != 1:
            raise AssertionError("Preview: el cierre no listo no está bloqueado")

        evidence = {
            "diagnostic": {
                "route": route,
                "price": price,
                "reasons": reasons.count(),
                "persistent": True,
            },
            "first_year": {
                "stages": 4,
                "routes": 3,
                "keyboard": "ok",
                "advanced": "ok",
            },
            "preview_closure": {
                "gates": 5,
                "state": "NO LISTO",
                "fail_closed": True,
            },
        }
        (ARTIFACT_DIR / "site-journey-evidence.json").write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        context.close()
        browser.close()
        print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
