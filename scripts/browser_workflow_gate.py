from __future__ import annotations

import json
import os
from pathlib import Path

from playwright.sync_api import BrowserType, Page, sync_playwright

BASE_URL = os.environ.get("BROWSER_GATE_BASE_URL", "http://127.0.0.1:8765").rstrip("/")
BROWSER_NAME = os.environ.get("BROWSER", "chromium").strip().lower()
ARTIFACT_DIR = Path(os.environ.get("BROWSER_GATE_ARTIFACT_DIR", "browser-gate-artifacts")).resolve()
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

VIEWPORTS = (
    ("desktop-1440", 1440, 900),
    ("desktop-1024", 1024, 768),
    ("mobile-390", 390, 844),
    ("mobile-360", 360, 800),
)


def _browser_type(playwright) -> BrowserType:
    mapping = {
        "chromium": playwright.chromium,
        "firefox": playwright.firefox,
        "webkit": playwright.webkit,
    }
    try:
        return mapping[BROWSER_NAME]
    except KeyError as exc:
        raise SystemExit(f"Motor no soportado: {BROWSER_NAME}") from exc


def _login(page: Page) -> None:
    page.goto(f"{BASE_URL}/login", wait_until="networkidle")
    page.locator('input[name="email"]').fill("admin@calculatuhuella.local")
    page.locator('input[name="password"]').fill("Demo2026!")
    page.locator("form.login-form button").click()
    page.wait_for_load_state("networkidle")
    if "/login" in page.url:
        raise AssertionError("El inicio de sesión demo no salió de /login.")
    page.evaluate("window.localStorage.setItem('cth-tour-v14-administrador', 'completed')")


def _close_transient_dialogs(page: Page) -> None:
    page.evaluate(
        """
        () => document.querySelectorAll('dialog[open]').forEach((dialog) => {
          try { dialog.close(); } catch (_error) { dialog.removeAttribute('open'); }
        })
        """
    )


def _accessibility_contract(page: Page) -> dict[str, object]:
    h1 = page.locator("h1").first
    h1.wait_for(state="visible")
    if "Mi trabajo" not in h1.inner_text():
        raise AssertionError("/mi-trabajo no presenta el encabezado esperado.")

    current = page.locator('.nav-item[aria-current="page"]')
    if current.count() != 1 or "Mi trabajo" not in current.first.inner_text():
        raise AssertionError("La navegación no marca Mi trabajo como página actual.")

    unnamed = page.evaluate(
        """
        () => [...document.querySelectorAll('input:not([type=hidden]), select, textarea')]
          .filter((control) => {
            const label = control.closest('label');
            const named = control.getAttribute('aria-label') || control.getAttribute('aria-labelledby');
            const hint = control.getAttribute('placeholder') || control.getAttribute('title');
            return !(label || named || hint);
          })
          .map((control) => control.outerHTML.slice(0, 160))
        """
    )
    if unnamed:
        raise AssertionError(f"Controles sin nombre accesible: {unnamed}")

    page.keyboard.press("Tab")
    focus = page.evaluate(
        """
        () => ({
          tag: document.activeElement?.tagName || '',
          text: (document.activeElement?.innerText || document.activeElement?.getAttribute?.('aria-label') || '').trim().slice(0, 100),
          body: document.activeElement === document.body,
        })
        """
    )
    if focus["body"] or not focus["tag"]:
        raise AssertionError("La navegación por teclado no mueve el foco a un elemento interactivo.")
    return {"current_navigation": current.first.inner_text().strip(), "first_tab_focus": focus}


def _overflow_offenders(page: Page) -> list[dict[str, object]]:
    return page.evaluate(
        """
        () => {
          const viewport = document.documentElement.clientWidth;
          const describe = (element) => {
            const rect = element.getBoundingClientRect();
            const className = typeof element.className === 'string' ? element.className.trim() : '';
            const classes = className ? '.' + className.split(/\s+/).filter(Boolean).slice(0, 4).join('.') : '';
            const selector = `${element.tagName.toLowerCase()}${element.id ? '#' + element.id : ''}${classes}`;
            return {
              selector,
              left: Math.round(rect.left * 10) / 10,
              right: Math.round(rect.right * 10) / 10,
              width: Math.round(rect.width * 10) / 10,
              scrollWidth: element.scrollWidth,
              clientWidth: element.clientWidth,
              text: (element.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 120),
            };
          };
          return [...document.querySelectorAll('body *')]
            .map(describe)
            .filter((item) => item.right > viewport + 1 || item.left < -1 || item.scrollWidth > item.clientWidth + 1)
            .sort((a, b) => Math.max(b.right - viewport, b.scrollWidth - b.clientWidth) - Math.max(a.right - viewport, a.scrollWidth - a.clientWidth))
            .slice(0, 30);
        }
        """
    )


def _viewport_contract(page: Page, label: str, width: int, height: int) -> dict[str, object]:
    page.set_viewport_size({"width": width, "height": height})
    page.goto(f"{BASE_URL}/mi-trabajo?scope=all", wait_until="networkidle")
    _close_transient_dialogs(page)
    dimensions = page.evaluate(
        """
        () => ({
          clientWidth: document.documentElement.clientWidth,
          scrollWidth: document.documentElement.scrollWidth,
          bodyScrollWidth: document.body.scrollWidth,
        })
        """
    )
    overflow = max(dimensions["scrollWidth"], dimensions["bodyScrollWidth"]) - dimensions["clientWidth"]
    offenders = _overflow_offenders(page) if overflow > 1 else []

    page.locator("h1").first.wait_for(state="visible")
    screenshot = ARTIFACT_DIR / f"mi-trabajo-{BROWSER_NAME}-{label}.png"
    page.screenshot(path=str(screenshot), full_page=True)

    diagnostic = {
        "label": label,
        "width": width,
        "height": height,
        "overflow_px": overflow,
        "dimensions": dimensions,
        "offenders": offenders,
        "screenshot": screenshot.name,
    }
    if overflow > 1:
        diagnostic_path = ARTIFACT_DIR / f"overflow-{BROWSER_NAME}-{label}.json"
        diagnostic_path.write_text(json.dumps(diagnostic, ensure_ascii=False, indent=2), encoding="utf-8")
    return diagnostic


def main() -> int:
    console_errors: list[str] = []
    page_errors: list[str] = []
    result: dict[str, object] = {
        "browser_engine": BROWSER_NAME,
        "base_url": BASE_URL,
        "viewports": [],
    }

    with sync_playwright() as playwright:
        browser = _browser_type(playwright).launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        _login(page)
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: page_errors.append(str(error)))

        page.goto(f"{BASE_URL}/mi-trabajo?scope=all", wait_until="networkidle")
        _close_transient_dialogs(page)
        result["accessibility"] = _accessibility_contract(page)

        for label, width, height in VIEWPORTS:
            result["viewports"].append(_viewport_contract(page, label, width, height))

        result["console_errors"] = console_errors
        result["page_errors"] = page_errors
        evidence = ARTIFACT_DIR / f"browser-gate-{BROWSER_NAME}.json"
        evidence.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))

        overflow_failures = [row for row in result["viewports"] if row["overflow_px"] > 1]
        if overflow_failures:
            summary = [
                {
                    "label": row["label"],
                    "overflow_px": row["overflow_px"],
                    "top_offenders": row["offenders"][:6],
                }
                for row in overflow_failures
            ]
            raise AssertionError(f"Overflow horizontal detectado: {json.dumps(summary, ensure_ascii=False)}")
        if console_errors or page_errors:
            raise AssertionError(
                f"Errores de navegador detectados. console={console_errors}; page={page_errors}"
            )
        context.close()
        browser.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
