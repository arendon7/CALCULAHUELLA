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
CORE_SURFACE_VIEWPORTS = (
    ("desktop-1440", 1440, 900),
    ("mobile-390", 390, 844),
)
HISTORICAL_DOSSIER_VIEWPORTS = (
    ("desktop-1440", 1440, 900),
    ("mobile-390", 390, 844),
)
HISTORICAL_DOSSIER_SUFFIXES = (
    "",
    "/informacion",
    "/calculos",
    "/analisis",
    "/reduccion",
    "/reportes",
    "/entrega-profesional",
)
CORE_SURFACES = (
    ("inventarios", "/inventarios"),
    ("captura-guiada", "/captura-guiada"),
    ("calidad-datos", "/calidad-datos"),
    ("informes", "/reportes"),
    ("informacion", "/informacion"),
    ("calculos", "/calculos"),
    ("analisis", "/analisis"),
    ("reduccion", "/reduccion"),
    ("cierre-mensual", "/cierre-mensual"),
    ("control-profesional", "/control"),
    ("aseguramiento", "/aseguramiento"),
    ("verificacion", "/verificacion"),
    ("cierre-metodologico", "/metodologia/cierre"),
    ("gobierno-metodologico", "/gobierno-metodologico"),
)
WEBKIT_STYLE_ATTR_WARNING = "Refused to apply a stylesheet because"


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


def _tour_progress_contract(page: Page) -> dict[str, object]:
    state = page.evaluate(
        """
        () => {
          const dialog = document.getElementById('welcomeTourDialog');
          const track = dialog?.querySelector('.tour-progress');
          const bar = track?.querySelector('i');
          if (!dialog || !track || !bar) return { present: false };
          const wasOpen = dialog.hasAttribute('open');
          if (!wasOpen) dialog.setAttribute('open', '');
          const trackWidth = track.getBoundingClientRect().width;
          const barWidth = bar.getBoundingClientRect().width;
          const ratio = trackWidth > 0 ? barWidth / trackWidth : 0;
          if (!wasOpen) dialog.removeAttribute('open');
          return {
            present: true,
            track_width: Math.round(trackWidth * 10) / 10,
            bar_width: Math.round(barWidth * 10) / 10,
            ratio: Math.round(ratio * 1000) / 1000,
          };
        }
        """
    )
    if not state.get("present"):
        raise AssertionError("El recorrido guiado no expone su barra de progreso.")
    ratio = float(state.get("ratio") or 0)
    if not 0.23 <= ratio <= 0.27:
        raise AssertionError(f"El primer paso del tour no conserva progreso visual de 25%: {state}")
    return state


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
    return {
        "current_navigation": current.first.inner_text().strip(),
        "first_tab_focus": focus,
        "tour_progress": _tour_progress_contract(page),
    }


def _overflow_offenders(page: Page) -> list[dict[str, object]]:
    return page.evaluate(
        r"""
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


def _page_dimensions(page: Page) -> dict[str, int]:
    return page.evaluate(
        """
        () => ({
          clientWidth: document.documentElement.clientWidth,
          scrollWidth: document.documentElement.scrollWidth,
          bodyScrollWidth: document.body.scrollWidth,
        })
        """
    )


def _viewport_contract(page: Page, label: str, width: int, height: int) -> dict[str, object]:
    page.set_viewport_size({"width": width, "height": height})
    page.goto(f"{BASE_URL}/mi-trabajo?scope=all", wait_until="networkidle")
    _close_transient_dialogs(page)
    dimensions = _page_dimensions(page)
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


def _core_surface_visual_evidence(page: Page) -> list[dict[str, object]]:
    evidence: list[dict[str, object]] = []
    if BROWSER_NAME != "chromium":
        return evidence

    for slug, path in CORE_SURFACES:
        for viewport, width, height in CORE_SURFACE_VIEWPORTS:
            page.set_viewport_size({"width": width, "height": height})
            page.goto(f"{BASE_URL}{path}", wait_until="networkidle")
            _close_transient_dialogs(page)
            page.locator("h1").first.wait_for(state="visible")
            dimensions = _page_dimensions(page)
            overflow = max(dimensions["scrollWidth"], dimensions["bodyScrollWidth"]) - dimensions["clientWidth"]
            offenders = _overflow_offenders(page) if overflow > 1 else []
            screenshot = ARTIFACT_DIR / f"core-{slug}-{viewport}.png"
            page.screenshot(path=str(screenshot), full_page=True)
            row = {
                "surface": slug,
                "path": path,
                "viewport": viewport,
                "width": width,
                "height": height,
                "overflow_px": overflow,
                "dimensions": dimensions,
                "offenders": offenders,
                "screenshot": screenshot.name,
            }
            evidence.append(row)
            if overflow > 1:
                diagnostic_path = ARTIFACT_DIR / f"overflow-core-{slug}-{viewport}.json"
                diagnostic_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    return evidence


def _historical_dossier_contract(page: Page) -> dict[str, object]:
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(f"{BASE_URL}/inventarios", wait_until="networkidle")
    _close_transient_dialogs(page)

    historical = page.locator(
        '.inventory-card.historical-context .card-actions a.btn-primary[href^="/inventarios/"]'
    ).first
    if historical.count() != 1:
        raise AssertionError("El seed demo no expone un periodo histórico navegable en /inventarios.")
    dossier_root = historical.get_attribute("href") or ""
    if not dossier_root.startswith("/inventarios/") or dossier_root.count("/") != 2:
        raise AssertionError(f"Ruta histórica inesperada: {dossier_root!r}")

    expected_hrefs = [f"{dossier_root}{suffix}" for suffix in HISTORICAL_DOSSIER_SUFFIXES]
    viewport_evidence: list[dict[str, object]] = []

    for label, width, height in HISTORICAL_DOSSIER_VIEWPORTS:
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{BASE_URL}{dossier_root}", wait_until="networkidle")
        _close_transient_dialogs(page)

        dossier = page.locator("[data-inventory-dossier-nav]")
        if dossier.count() != 1:
            raise AssertionError(f"El expediente histórico no expone su navegación en {label}.")
        hrefs = dossier.locator("a[href]").evaluate_all("nodes => nodes.map(node => node.getAttribute('href'))")
        if hrefs != expected_hrefs:
            raise AssertionError(f"Rutas del expediente alteradas en {label}: {hrefs}")

        current = dossier.locator('a[aria-current="page"]')
        if current.count() != 1 or current.get_attribute("href") != dossier_root:
            raise AssertionError(f"La ficha histórica no queda marcada como vista actual en {label}.")

        period_pill = page.locator(f'.version-pill[href="{dossier_root}"]')
        if period_pill.count() != 1:
            raise AssertionError(f"La barra de contexto no conserva el periodo histórico en {label}.")

        metrics = dossier.evaluate(
            """
            (nav) => ({
              clientWidth: nav.clientWidth,
              scrollWidth: nav.scrollWidth,
              links: [...nav.querySelectorAll('a')].map((link) => {
                const rect = link.getBoundingClientRect();
                return {
                  href: link.getAttribute('href'),
                  visible: rect.width > 0 && rect.height > 0,
                  left: Math.round(rect.left * 10) / 10,
                  right: Math.round(rect.right * 10) / 10,
                };
              }),
            })
            """
        )
        nav_overflow = int(metrics["scrollWidth"]) - int(metrics["clientWidth"])
        if nav_overflow > 1:
            raise AssertionError(f"La navegación histórica desborda horizontalmente en {label}: {metrics}")
        if width <= 720:
            hidden = [row for row in metrics["links"] if not row["visible"]]
            outside = [
                row
                for row in metrics["links"]
                if float(row["left"]) < -1 or float(row["right"]) > width + 1
            ]
            if hidden or outside:
                raise AssertionError(
                    f"Las siete vistas históricas no permanecen visibles en móvil: hidden={hidden}; outside={outside}"
                )

        result_link = dossier.locator(f'a[href="{dossier_root}/calculos"]')
        result_link.click()
        page.wait_for_load_state("networkidle")
        if page.url != f"{BASE_URL}{dossier_root}/calculos":
            raise AssertionError(f"Resultados perdió el periodo histórico en {label}: {page.url}")

        preserving = page.locator('#navegacion-principal a[data-period-preserving="true"]')
        preserving_hrefs = preserving.evaluate_all("nodes => nodes.map(node => node.getAttribute('href'))")
        if not preserving_hrefs or any(not href.startswith(f"{dossier_root}/") for href in preserving_hrefs):
            raise AssertionError(
                f"El menú global expone enlaces que pierden el periodo histórico en {label}: {preserving_hrefs}"
            )

        if width > 720:
            information = page.locator(
                f'#navegacion-principal a[data-period-preserving="true"][href="{dossier_root}/informacion"]'
            )
            if information.count() != 1:
                raise AssertionError("El menú lateral no ofrece Datos preservando el periodo histórico.")
            information.click()
            page.wait_for_load_state("networkidle")
            if page.url != f"{BASE_URL}{dossier_root}/informacion":
                raise AssertionError(f"El menú lateral perdió el periodo histórico: {page.url}")

        screenshot_name = None
        if BROWSER_NAME == "chromium":
            screenshot = ARTIFACT_DIR / f"historical-dossier-{label}.png"
            page.screenshot(path=str(screenshot), full_page=True)
            screenshot_name = screenshot.name

        viewport_evidence.append(
            {
                "label": label,
                "width": width,
                "height": height,
                "dossier_root": dossier_root,
                "hrefs": hrefs,
                "period_preserving_hrefs": preserving_hrefs,
                "navigation_overflow_px": nav_overflow,
                "screenshot": screenshot_name,
            }
        )

    return {
        "dossier_root": dossier_root,
        "expected_hrefs": expected_hrefs,
        "viewports": viewport_evidence,
    }


def _known_webkit_style_warning(text: str) -> bool:
    return (
        BROWSER_NAME == "webkit"
        and WEBKIT_STYLE_ATTR_WARNING in text
        and "style-src directive" in text
        and "Content Security Policy" in text
    )


def main() -> int:
    console_errors: list[str] = []
    known_engine_warnings: list[str] = []
    page_errors: list[str] = []
    result: dict[str, object] = {
        "browser_engine": BROWSER_NAME,
        "base_url": BASE_URL,
        "viewports": [],
        "core_surfaces": [],
        "historical_dossier": {},
    }

    with sync_playwright() as playwright:
        browser = _browser_type(playwright).launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        _login(page)

        def record_console(message) -> None:
            if message.type != "error":
                return
            text = message.text
            if _known_webkit_style_warning(text):
                known_engine_warnings.append(text)
            else:
                console_errors.append(text)

        page.on("console", record_console)
        page.on("pageerror", lambda error: page_errors.append(str(error)))

        page.goto(f"{BASE_URL}/mi-trabajo?scope=all", wait_until="networkidle")
        _close_transient_dialogs(page)
        result["accessibility"] = _accessibility_contract(page)

        for label, width, height in VIEWPORTS:
            result["viewports"].append(_viewport_contract(page, label, width, height))

        result["core_surfaces"] = _core_surface_visual_evidence(page)
        result["historical_dossier"] = _historical_dossier_contract(page)
        result["console_errors"] = console_errors
        result["known_engine_warnings"] = known_engine_warnings
        result["page_errors"] = page_errors
        evidence = ARTIFACT_DIR / f"browser-gate-{BROWSER_NAME}.json"
        evidence.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))

        overflow_failures = [row for row in result["viewports"] if row["overflow_px"] > 1]
        overflow_failures.extend(row for row in result["core_surfaces"] if row["overflow_px"] > 1)
        if overflow_failures:
            summary = [
                {
                    "label": row.get("label") or f"{row.get('surface')}:{row.get('viewport')}",
                    "overflow_px": row["overflow_px"],
                    "top_offenders": row["offenders"][:6],
                }
                for row in overflow_failures
            ]
            raise AssertionError(f"Overflow horizontal detectado: {json.dumps(summary, ensure_ascii=False)}")
        if len(known_engine_warnings) > len(VIEWPORTS) + 1:
            raise AssertionError(
                f"WebKit produjo más avisos CSP conocidos de los esperados: {len(known_engine_warnings)}"
            )
        if console_errors or page_errors:
            raise AssertionError(
                f"Errores de navegador detectados. console={console_errors}; page={page_errors}"
            )
        context.close()
        browser.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
