from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Page, Route, sync_playwright

BASE_URL = os.environ.get("SITE_PREVIEW_BASE_URL", "http://127.0.0.1:8780").rstrip("/")
APP_BASE_URL = "https://calcula-tu-huella-arendon7-preview.onrender.com"
ARTIFACT_DIR = Path(os.environ.get("SITE_PREVIEW_ARTIFACT_DIR", "site-preview-artifacts")).resolve()
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = Path("site/config.js")
PII_FIELDS = ("company_name", "contact_name", "email", "phone")


def _clear(page: Page) -> None:
    page.goto(BASE_URL, wait_until="domcontentloaded")
    page.locator("h1").wait_for(state="visible")
    page.evaluate("localStorage.clear()")
    page.reload(wait_until="domcontentloaded")
    page.locator("h1").wait_for(state="visible")
    page.locator("[data-diagnostic-form]").wait_for(state="visible")


def _fill_essential(page: Page) -> None:
    form = page.locator("[data-diagnostic-form]")
    form.locator('select[name="sector"]').select_option("servicios")
    form.locator('input[name="sedes"]').fill("1")
    form.locator('select[name="primera"]').select_option("si")
    form.locator('select[name="datos"]').select_option("alta")
    form.locator('select[name="objetivo"]').select_option("medir")
    form.locator('button[type="submit"]').click()
    page.locator('[data-result-route]').wait_for(state="visible")
    if page.locator('[data-result-route]').inner_text().strip() != "Huella Esencial":
        raise AssertionError("La ruta base de handoff dejó de ser Huella Esencial")


def _assert_brief(dialog) -> dict[str, str]:
    observed = {
        "route": dialog.locator('[data-brief-route]').inner_text().strip(),
        "price": dialog.locator('[data-brief-price]').inner_text().strip(),
        "sector": dialog.locator('[data-brief-sector]').inner_text().strip(),
        "sites": dialog.locator('[data-brief-sites]').inner_text().strip(),
    }
    expected = {
        "route": "Huella Esencial",
        "price": "$1.300.000 COP / año",
        "sector": "Servicios y oficinas",
        "sites": "1",
    }
    if observed != expected:
        raise AssertionError(f"Ficha inesperada: {observed}")
    return observed


def _storage_without_pii(page: Page) -> list[str]:
    storage = page.evaluate(
        """
        () => Object.fromEntries(Object.keys(localStorage).map(key => [key, localStorage.getItem(key)]))
        """
    )
    serialized = json.dumps(storage, ensure_ascii=False).lower()
    forbidden = ("company_name", "contact_name", '"email"', '"phone"', "correo:", "teléfono:")
    if any(term in serialized for term in forbidden):
        raise AssertionError(f"Pages persistió PII en localStorage: {storage}")
    return sorted(storage)


def _assert_no_pii_form(dialog) -> None:
    if dialog.locator('[data-route-contact-form]').count():
        raise AssertionError("Pages no debe contener un formulario POST de contacto")
    for field in PII_FIELDS:
        if dialog.locator(f'[name="{field}"]').count():
            raise AssertionError(f"Pages no debe solicitar PII: {field}")


def _offline_contract(browser) -> dict[str, object]:
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    posts: list[str] = []
    page.on("request", lambda request: posts.append(request.url) if request.method == "POST" else None)

    def blank_config(route: Route) -> None:
        route.fulfill(
            status=200,
            content_type="application/javascript",
            body='window.CALCULA_TU_HUELLA_CONFIG = { appBaseUrl: "" };',
        )

    page.route("**/config.js", blank_config)
    _clear(page)
    _fill_essential(page)
    page.locator('[data-route-card-open]').click()
    dialog = page.locator('[data-route-card-dialog]')
    if not dialog.locator('[data-route-app-offline]').is_visible():
        raise AssertionError("Sin appBaseUrl debe mantenerse el aviso de preview")
    if dialog.locator('[data-route-app-bridge]').is_visible():
        raise AssertionError("Sin appBaseUrl no debe aparecer el bridge")
    _assert_no_pii_form(dialog)
    if posts:
        raise AssertionError(f"El modo offline generó POST inesperados: {posts}")
    storage_keys = _storage_without_pii(page)
    context.close()
    return {"posts": posts, "storage_keys": storage_keys}


def _connected_contract(browser) -> dict[str, object]:
    config = CONFIG_PATH.read_text(encoding="utf-8")
    if APP_BASE_URL not in config:
        raise AssertionError("site/config.js no apunta al staging Render certificado")

    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    context.grant_permissions(["clipboard-read", "clipboard-write"], origin=BASE_URL)
    page = context.new_page()
    posts: list[str] = []
    page.on("request", lambda request: posts.append(request.url) if request.method == "POST" else None)
    page.add_init_script("window.print = () => { window.__cthPrinted = true; };")
    _clear(page)

    open_button = page.locator('[data-route-card-open]')
    if not open_button.is_disabled():
        raise AssertionError("La ficha debe iniciar deshabilitada sin diagnóstico")
    _fill_essential(page)
    page.wait_for_timeout(80)
    if open_button.is_disabled():
        raise AssertionError("La ficha no se habilitó después del diagnóstico")
    open_button.click()

    dialog = page.locator('[data-route-card-dialog]')
    if not dialog.is_visible():
        raise AssertionError("La ficha de ruta no abrió")
    brief = _assert_brief(dialog)
    if not dialog.locator('[data-route-app-bridge]').is_visible():
        raise AssertionError("El staging configurado no habilitó el bridge")
    if dialog.locator('[data-route-app-offline]').is_visible():
        raise AssertionError("El aviso offline siguió visible con staging certificado")

    diagnosis_href = dialog.locator('[data-route-app-diagnostic]').get_attribute("href")
    privacy_href = dialog.locator('[data-contact-privacy]').get_attribute("href")
    contact = dialog.locator('[data-route-contact-open]')
    contact_href = contact.get_attribute("href") or ""
    if diagnosis_href != f"{APP_BASE_URL}/diagnostico":
        raise AssertionError(f"Handoff de diagnóstico inesperado: {diagnosis_href}")
    if privacy_href != f"{APP_BASE_URL}/legal/privacidad":
        raise AssertionError(f"Handoff de privacidad inesperado: {privacy_href}")
    if contact.evaluate("el => el.tagName") != "A":
        raise AssertionError("Solicitar revisión debe ser una navegación GET, no un formulario")

    parsed = urlparse(contact_href)
    expected_origin = urlparse(APP_BASE_URL)
    if (parsed.scheme, parsed.netloc, parsed.path) != (expected_origin.scheme, expected_origin.netloc, "/contacto"):
        raise AssertionError(f"Destino de contacto inesperado: {contact_href}")
    params = parse_qs(parsed.query, keep_blank_values=True)
    expected_params = {
        "plan": ["Huella Esencial"],
        "sector": ["Servicios y oficinas"],
        "sites": ["1"],
        "objective": ["Construir la primera huella"],
    }
    if params != expected_params:
        raise AssertionError(f"El handoff GET transfirió parámetros inesperados: {params}")
    if any(key in params for key in PII_FIELDS):
        raise AssertionError(f"El handoff GET contiene PII: {params}")
    _assert_no_pii_form(dialog)

    dialog.locator('[data-route-copy]').click()
    page.wait_for_timeout(80)
    status = dialog.locator('[data-route-card-status]').inner_text().strip().lower()
    if "copiado" not in status:
        raise AssertionError(f"Copiar ficha no confirmó resultado: {status!r}")
    clipboard = page.evaluate("navigator.clipboard.readText()")
    required_copy = ("Huella Esencial", "$1.300.000 COP / año", "Servicios y oficinas")
    if not all(value in clipboard for value in required_copy):
        raise AssertionError("El resumen copiado perdió datos esenciales")
    if any(term in clipboard.lower() for term in ("company_name", "contact_name", "correo:", "teléfono:")):
        raise AssertionError("La ficha copiada contiene etiquetas PII")

    dialog.locator('[data-route-print]').click()
    page.wait_for_timeout(50)
    printed = page.evaluate("Boolean(window.__cthPrinted)")
    printing_class = page.evaluate("document.body.classList.contains('route-card-printing')")
    print_text = page.locator('[data-route-print-surface]').inner_text()
    if not printed or not printing_class or "Huella Esencial" not in print_text:
        raise AssertionError("El flujo imprimir/guardar PDF no preparó la ficha")
    page.evaluate("window.dispatchEvent(new Event('afterprint'))")
    if page.evaluate("document.body.classList.contains('route-card-printing')"):
        raise AssertionError("El estado de impresión no se limpió")

    storage_keys = _storage_without_pii(page)
    if posts:
        raise AssertionError(f"Pages generó POST cross-origin o silencioso: {posts}")
    page.screenshot(path=str(ARTIFACT_DIR / "route-handoff-desktop.png"), full_page=True)
    context.close()
    return {
        "brief": brief,
        "diagnosis": diagnosis_href,
        "privacy": privacy_href,
        "contact_get": contact_href,
        "contact_params": params,
        "posts": posts,
        "storage_keys": storage_keys,
    }


def _mobile(browser) -> dict[str, object]:
    context = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
    page = context.new_page()
    _clear(page)
    _fill_essential(page)
    page.wait_for_timeout(80)
    page.locator('[data-route-card-open]').click()
    dialog = page.locator('[data-route-card-dialog]')
    page.wait_for_timeout(100)
    if not dialog.locator('[data-route-app-bridge]').is_visible():
        raise AssertionError("El bridge conectado desapareció en móvil")
    metrics = dialog.evaluate(
        """
        el => ({
          viewport: window.innerWidth,
          dialog_left: el.getBoundingClientRect().left,
          dialog_right: el.getBoundingClientRect().right,
          dialog_width: el.getBoundingClientRect().width,
          scroll_width: el.scrollWidth,
          client_width: el.clientWidth,
          doc_width: document.documentElement.scrollWidth,
        })
        """
    )
    if metrics["dialog_left"] < -1 or metrics["dialog_right"] > metrics["viewport"] + 1:
        raise AssertionError(f"La ficha móvil sale del viewport: {metrics}")
    if metrics["doc_width"] > metrics["viewport"] + 1:
        raise AssertionError(f"El handoff creó overflow horizontal móvil: {metrics}")
    page.screenshot(path=str(ARTIFACT_DIR / "route-handoff-mobile.png"), full_page=True)
    context.close()
    return metrics


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        evidence = {
            "offline_fallback": _offline_contract(browser),
            "connected_staging_contract": _connected_contract(browser),
            "mobile": _mobile(browser),
        }
        browser.close()
    (ARTIFACT_DIR / "site-route-handoff-evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
