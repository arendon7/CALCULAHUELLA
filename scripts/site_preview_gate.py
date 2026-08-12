from __future__ import annotations

import json
import os
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

BASE_URL = os.environ.get("SITE_PREVIEW_BASE_URL", "http://127.0.0.1:8780").rstrip("/")
ARTIFACT_DIR = Path(os.environ.get("SITE_PREVIEW_ARTIFACT_DIR", "site-preview-artifacts")).resolve()
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def _browser_errors(page: Page) -> tuple[list[str], list[str]]:
    console_errors: list[str] = []
    page_errors: list[str] = []
    page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    return console_errors, page_errors


def _layout_state(page: Page) -> dict[str, object]:
    return page.evaluate(
        """
        () => {
          const experience = document.querySelector('#experiencia');
          const years = experience?.querySelector('.experience-years');
          const diagnostic = document.querySelector('#diagnostico');
          const finalCta = document.querySelector('.craft-final-cta');
          const prototype = document.querySelector('.craft-prototype-note');
          const er = experience?.getBoundingClientRect();
          const yr = years?.getBoundingClientRect();
          return {
            viewport: window.innerWidth,
            document_width: document.documentElement.scrollWidth,
            body_width: document.body.scrollWidth,
            overflow: Math.max(
              0,
              document.documentElement.scrollWidth - window.innerWidth,
              document.body.scrollWidth - window.innerWidth
            ),
            h1_count: document.querySelectorAll('h1').length,
            visible_eyebrows: [...document.querySelectorAll('.eyebrow,.eyebrow-light')]
              .filter(el => getComputedStyle(el).display !== 'none').length,
            dead_links: [...document.querySelectorAll('a[href="#"]')].length,
            price_section: Boolean(document.querySelector('#precios')),
            demo_section: Boolean(document.querySelector('#demo-app')),
            skip_link: Boolean(document.querySelector('.skip-link[href="#contenido"]')),
            experience_years_contained: Boolean(er && yr && yr.top >= er.top - 1 && yr.bottom <= er.bottom + 1),
            final_cta_after_diagnostic: Boolean(
              diagnostic && finalCta &&
              (diagnostic.compareDocumentPosition(finalCta) & Node.DOCUMENT_POSITION_FOLLOWING)
            ),
            final_cta_before_prototype: Boolean(
              finalCta && prototype &&
              (finalCta.compareDocumentPosition(prototype) & Node.DOCUMENT_POSITION_FOLLOWING)
            ),
          };
        }
        """
    )


def _assert_base_contract(page: Page, label: str) -> dict[str, object]:
    state = _layout_state(page)
    if int(state["overflow"]) > 1:
        raise AssertionError(f"{label}: overflow horizontal {state}")
    if state["h1_count"] != 1:
        raise AssertionError(f"{label}: se esperaba exactamente un H1: {state}")
    if state["visible_eyebrows"] != 0:
        raise AssertionError(f"{label}: quedan eyebrows visibles: {state}")
    if state["dead_links"] != 0:
        raise AssertionError(f"{label}: existen enlaces href=# sin destino: {state}")
    if not state["price_section"] or not state["demo_section"] or not state["skip_link"]:
        raise AssertionError(f"{label}: falta una superficie pública crítica: {state}")
    if not state["experience_years_contained"]:
        raise AssertionError(f"{label}: el bloque de experiencia escapó de su sección: {state}")
    if not state["final_cta_after_diagnostic"] or not state["final_cta_before_prototype"]:
        raise AssertionError(f"{label}: el CTA final no cierra el recorrido real: {state}")
    return state


def _assert_prices(page: Page) -> dict[str, str]:
    text = page.locator("#precios").inner_text()
    expected = {
        "essential": "$1.300.000",
        "management": "$3.300.000",
        "advanced": "$8.300.000",
    }
    for key, value in expected.items():
        if value not in text:
            raise AssertionError(f"Pricing: falta {key}={value}")
    if "COP / año" not in text:
        raise AssertionError("Pricing: falta la unidad anual COP")
    return expected


def _assert_diagnostic(page: Page) -> dict[str, str]:
    page.locator('select[name="sector"]').select_option("servicios")
    page.locator('input[name="sedes"]').fill("1")
    page.locator('select[name="primera"]').select_option("si")
    page.locator('select[name="datos"]').select_option("alta")
    page.locator('select[name="objetivo"]').select_option("medir")
    page.locator('[data-diagnostic-form] button[type="submit"]').click()
    route = page.locator('[data-result-route]').inner_text().strip()
    price = page.locator('[data-result-price]').inner_text().strip()
    if route != "Huella Esencial":
        raise AssertionError(f"Diagnóstico: ruta inesperada {route!r}")
    if "$1.300.000 COP / año" not in price:
        raise AssertionError(f"Diagnóstico: precio inesperado {price!r}")
    return {"route": route, "price": price}


def _assert_demo(page: Page) -> dict[str, str]:
    calc = page.locator('[data-preview-view="calculo"]')
    calc.click()
    panel = page.locator('[data-preview-panel="calculo"]')
    if not panel.is_visible():
        raise AssertionError("Demo: Cálculo no se volvió visible")
    result = panel.locator('.preview-result strong').inner_text().strip()
    role = page.locator('[data-preview-role-select]')
    role.select_option("Verificador")
    label = page.locator('[data-preview-role]').inner_text().strip()
    if label != "Verificador":
        raise AssertionError(f"Demo: selector de rol no actualizó la etiqueta: {label!r}")
    return {"result": result, "role": label}


def _desktop(browser) -> dict[str, object]:
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = context.new_page()
    console_errors, page_errors = _browser_errors(page)
    page.goto(BASE_URL, wait_until="domcontentloaded")
    page.locator("h1").wait_for(state="visible")
    page.wait_for_timeout(600)
    layout = _assert_base_contract(page, "desktop")
    prices = _assert_prices(page)
    diagnostic = _assert_diagnostic(page)
    demo = _assert_demo(page)
    page.screenshot(path=str(ARTIFACT_DIR / "landing-desktop-1440.png"), full_page=True)
    if console_errors or page_errors:
        raise AssertionError(f"desktop browser errors: console={console_errors}, page={page_errors}")
    context.close()
    return {"layout": layout, "prices": prices, "diagnostic": diagnostic, "demo": demo}


def _mobile(browser) -> dict[str, object]:
    context = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
    page = context.new_page()
    console_errors, page_errors = _browser_errors(page)
    page.goto(BASE_URL, wait_until="domcontentloaded")
    page.locator("h1").wait_for(state="visible")
    page.wait_for_timeout(500)
    layout = _assert_base_contract(page, "mobile")
    menu = page.locator('[data-menu-button]')
    if not menu.is_visible():
        raise AssertionError("mobile: botón de menú no visible")
    menu.click()
    panel = page.locator('[data-mobile-panel]')
    if "open" not in (panel.get_attribute("class") or ""):
        raise AssertionError("mobile: el menú no abrió")
    if not panel.locator('a[href="#precios"]').is_visible():
        raise AssertionError("mobile: Precios no es descubrible en menú")
    page.keyboard.press("Escape")
    if "open" in (panel.get_attribute("class") or ""):
        raise AssertionError("mobile: Escape no cerró el menú")
    page.screenshot(path=str(ARTIFACT_DIR / "landing-mobile-390.png"), full_page=True)
    if console_errors or page_errors:
        raise AssertionError(f"mobile browser errors: console={console_errors}, page={page_errors}")
    context.close()
    return {"layout": layout, "menu": "ok"}


def _reduced_motion(browser) -> dict[str, object]:
    context = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    page = context.new_page()
    page.goto(BASE_URL, wait_until="domcontentloaded")
    page.locator("h1").wait_for(state="visible")
    page.wait_for_timeout(250)
    state = page.evaluate(
        """
        () => {
          const stage = document.querySelector('[data-craft-stage]');
          const style = stage ? getComputedStyle(stage) : null;
          return {
            present: Boolean(stage),
            transform: style?.transform || '',
            transition_duration: style?.transitionDuration || '',
          };
        }
        """
    )
    if not state["present"]:
        raise AssertionError("reduced-motion: hero craft stage ausente")
    if state["transform"] not in {"none", "matrix(1, 0, 0, 1, 0, 0)"}:
        raise AssertionError(f"reduced-motion: transform activo {state}")
    context.close()
    return state


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        evidence = {
            "desktop": _desktop(browser),
            "mobile": _mobile(browser),
            "reduced_motion": _reduced_motion(browser),
        }
        browser.close()
    (ARTIFACT_DIR / "site-preview-evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
