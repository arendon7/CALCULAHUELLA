from __future__ import annotations

import json
import os
from pathlib import Path

from playwright.sync_api import Page, Route, sync_playwright

BASE_URL = os.environ.get("SITE_PREVIEW_BASE_URL", "http://127.0.0.1:8780").rstrip("/")
ARTIFACT_DIR = Path(os.environ.get("SITE_PREVIEW_ARTIFACT_DIR", "site-preview-artifacts")).resolve()
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


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


def _privacy_safe_pages(browser) -> dict[str, object]:
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    context.grant_permissions(["clipboard-read", "clipboard-write"], origin=BASE_URL)
    page = context.new_page()
    posts: list[str] = []
    page.on("request", lambda request: posts.append(request.url) if request.method == "POST" else None)
    page.add_init_script("window.print = () => { window.__cthPrinted = true; };")
    _clear(page)

    open_button = page.locator('[data-route-card-open]')
    if not open_button.is_disabled():
        raise AssertionError("La ficha de ruta debe iniciar deshabilitada sin diagnóstico")

    _fill_essential(page)
    page.wait_for_timeout(80)
    if open_button.is_disabled():
        raise AssertionError("La ficha no se habilitó después del diagnóstico")
    open_button.click()

    dialog = page.locator('[data-route-card-dialog]')
    if not dialog.is_visible():
        raise AssertionError("La ficha de ruta no abrió")
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

    if not dialog.locator('[data-route-app-offline]').is_visible():
        raise AssertionError("Pages debe declarar modo preview cuando appBaseUrl está vacío")
    if dialog.locator('[data-route-app-bridge]').is_visible():
        raise AssertionError("Pages no debe mostrar handoff a una app no configurada")
    if dialog.locator('[data-route-contact]').is_visible():
        raise AssertionError("Pages no debe pedir PII en la ficha inicial")

    dialog.locator('[data-route-copy]').click()
    page.wait_for_timeout(80)
    status = dialog.locator('[data-route-card-status]').inner_text().strip().lower()
    if "copiado" not in status:
        raise AssertionError(f"Copiar ficha no confirmó resultado: {status!r}")
    clipboard = page.evaluate("navigator.clipboard.readText()")
    required_copy = ("Huella Esencial", "$1.300.000 COP / año", "Servicios y oficinas")
    if not all(value in clipboard for value in required_copy):
        raise AssertionError("El resumen copiado perdió datos esenciales de la ficha")
    pii_terms = ("company_name", "contact_name", "email", "phone", "correo:", "teléfono:")
    if any(term.lower() in clipboard.lower() for term in pii_terms):
        raise AssertionError("La ficha copiada contiene campos o etiquetas PII")

    dialog.locator('[data-route-print]').click()
    page.wait_for_timeout(50)
    printed = page.evaluate("Boolean(window.__cthPrinted)")
    printing_class = page.evaluate("document.body.classList.contains('route-card-printing')")
    print_text = page.locator('[data-route-print-surface]').inner_text()
    if not printed or not printing_class or "Huella Esencial" not in print_text:
        raise AssertionError("El flujo imprimir/guardar PDF no preparó una ficha aislada")
    page.evaluate("window.dispatchEvent(new Event('afterprint'))")
    if page.evaluate("document.body.classList.contains('route-card-printing')"):
        raise AssertionError("El estado de impresión no se limpió después de afterprint")

    storage = page.evaluate(
        """
        () => Object.fromEntries(Object.keys(localStorage).map(key => [key, localStorage.getItem(key)]))
        """
    )
    serialized = json.dumps(storage, ensure_ascii=False).lower()
    forbidden_storage = ("company_name", "contact_name", '"email"', '"phone"')
    if any(term in serialized for term in forbidden_storage):
        raise AssertionError(f"Pages persistió PII en localStorage: {storage}")
    if posts:
        raise AssertionError(f"Pages generó POST sin app pública ni consentimiento: {posts}")

    dialog.locator('[data-route-card-close]').click()
    page.screenshot(path=str(ARTIFACT_DIR / "route-handoff-desktop.png"), full_page=True)
    context.close()
    return {"brief": observed, "posts": posts, "storage_keys": sorted(storage)}


def _connected_contract(browser) -> dict[str, object]:
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()

    def config_route(route: Route) -> None:
        route.fulfill(
            status=200,
            content_type="application/javascript",
            body='window.CALCULA_TU_HUELLA_CONFIG = { appBaseUrl: "https://app.example.test" };',
        )

    page.route("**/config.js", config_route)
    _clear(page)
    _fill_essential(page)
    page.wait_for_timeout(80)
    page.locator('[data-route-card-open]').click()
    dialog = page.locator('[data-route-card-dialog]')

    if not dialog.locator('[data-route-app-bridge]').is_visible():
        raise AssertionError("Una appBaseUrl configurada no habilitó el bridge")
    if dialog.locator('[data-route-app-offline]').is_visible():
        raise AssertionError("El aviso offline siguió visible con app configurada")

    diagnosis_href = dialog.locator('[data-route-app-diagnostic]').get_attribute("href")
    privacy_href = dialog.locator('[data-contact-privacy]').get_attribute("href")
    form_action = dialog.locator('[data-route-contact-form]').get_attribute("action")
    form_method = (dialog.locator('[data-route-contact-form]').get_attribute("method") or "").lower()
    expected = {
        "diagnosis": "https://app.example.test/diagnostico",
        "privacy": "https://app.example.test/legal/privacidad",
        "contact": "https://app.example.test/contacto",
        "method": "post",
    }
    observed = {
        "diagnosis": diagnosis_href,
        "privacy": privacy_href,
        "contact": form_action,
        "method": form_method,
    }
    if observed != expected:
        raise AssertionError(f"Contrato de handoff a app divergente: {observed}")

    dialog.locator('[data-route-contact-open]').click()
    contact = dialog.locator('[data-route-contact]')
    if not contact.is_visible():
        raise AssertionError("Solicitar revisión no mostró formulario")
    if contact.locator('input[name="accept_privacy"][required]').count() != 1:
        raise AssertionError("El formulario real perdió consentimiento de privacidad obligatorio")
    if contact.locator('input[name="interest"]').input_value() != "Huella Esencial":
        raise AssertionError("El handoff perdió el plan recomendado esperado por /contacto")
    if contact.locator('input[name="sector"]').input_value() != "Servicios y oficinas":
        raise AssertionError("El handoff perdió el sector del diagnóstico")
    if not contact.locator('[data-contact-message]').input_value().startswith("Quiero revisar la ruta orientativa Huella Esencial"):
        raise AssertionError("El mensaje real no incorpora el contexto del diagnóstico")

    context.close()
    return observed


def _mobile(browser) -> dict[str, object]:
    context = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
    page = context.new_page()
    _clear(page)
    _fill_essential(page)
    page.wait_for_timeout(80)
    page.locator('[data-route-card-open]').click()
    dialog = page.locator('[data-route-card-dialog]')
    page.wait_for_timeout(100)
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
            "pages_privacy_boundary": _privacy_safe_pages(browser),
            "connected_app_contract": _connected_contract(browser),
            "mobile": _mobile(browser),
        }
        browser.close()
    (ARTIFACT_DIR / "site-route-handoff-evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
