from __future__ import annotations

import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get("SITE_PREVIEW_BASE_URL", "http://127.0.0.1:8780").rstrip("/")
ARTIFACT_DIR = Path(os.environ.get("SITE_PREVIEW_ARTIFACT_DIR", "site-preview-artifacts")).resolve()

EXPECTED_FRAMEWORKS = {
    "GHG Protocol Corporate Standard": "https://ghgprotocol.org/corporate-standard",
    "GHG Protocol Scope 2 Guidance": "https://ghgprotocol.org/scope-2-guidance",
    "GHG Protocol Scope 3 Standard": "https://ghgprotocol.org/corporate-value-chain-scope-3-standard",
    "ISO 14064-1:2018": "https://www.iso.org/standard/66453.html",
    "IPCC 2006 + Refinamiento 2019": "https://www.ipcc-nggip.iges.or.jp/public/2019rf/index.html",
    "GHG Protocol LSR Standard v1.1": "https://ghgprotocol.org/land-sector-and-removals-standard",
}
EXPECTED_OFFERS = {
    "Huella Esencial": "1300000",
    "Gestión de Carbono": "3300000",
    "Gestión Avanzada": "8300000",
}


def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page.goto(BASE_URL, wait_until="domcontentloaded")
        page.locator("h1").wait_for(state="visible")
        page.wait_for_timeout(350)

        frameworks = page.locator("#marcos-metodologicos .framework-ledger a")
        if frameworks.count() != 6:
            raise AssertionError(f"Se esperaban 6 marcos metodológicos, hay {frameworks.count()}")
        observed: dict[str, str] = {}
        for index in range(frameworks.count()):
            link = frameworks.nth(index)
            title = link.locator("strong").inner_text().strip()
            href = link.get_attribute("href") or ""
            observed[title] = href
            if link.get_attribute("target") != "_blank":
                raise AssertionError(f"Marco externo sin target=_blank: {title}")
            rel = set((link.get_attribute("rel") or "").split())
            if not {"noopener", "noreferrer"}.issubset(rel):
                raise AssertionError(f"Marco externo sin rel seguro: {title} -> {rel}")
        if observed != EXPECTED_FRAMEWORKS:
            raise AssertionError(f"Marcos metodológicos inesperados: {observed}")

        method_text = page.locator("#marcos-metodologicos").inner_text()
        required_truth = (
            "no significa certificación",
            "conformidad automática",
            "verificación externa",
            "vigencia desde 1 ene 2027",
            "no declara por sí sola neutralidad",
            "conformidad ISO",
            "verificación independiente",
        )
        lowered = method_text.lower()
        for phrase in required_truth:
            if phrase.lower() not in lowered:
                raise AssertionError(f"Truth lock metodológico ausente: {phrase}")

        schemas = page.evaluate(
            """
            () => [...document.querySelectorAll('script[type="application/ld+json"]')]
              .map(node => JSON.parse(node.textContent))
            """
        )
        if len(schemas) != 2:
            raise AssertionError(f"Se esperaban 2 bloques JSON-LD, hay {len(schemas)}")
        webapp = next((item for item in schemas if item.get("@type") == "WebApplication"), None)
        faq = next((item for item in schemas if item.get("@type") == "FAQPage"), None)
        if not webapp or not faq:
            raise AssertionError(f"JSON-LD incompleto: {schemas}")
        offers = {item.get("name"): item.get("price") for item in webapp.get("offers", [])}
        if offers != EXPECTED_OFFERS:
            raise AssertionError(f"Precios JSON-LD no coinciden con oferta pública: {offers}")
        if any(item.get("priceCurrency") != "COP" for item in webapp.get("offers", [])):
            raise AssertionError("JSON-LD contiene una oferta sin moneda COP")
        if len(faq.get("mainEntity", [])) != 8:
            raise AssertionError("FAQPage JSON-LD no refleja las 8 preguntas visibles")

        if page.locator(".craft-action-card button").count() != 0:
            raise AssertionError("Hero volvió a exponer un botón visual muerto")
        if page.locator(".craft-action-card a[href='#demo-app']").count() != 1:
            raise AssertionError("Hero no enlaza su acción visual con la demo")
        if page.locator(".decision-action button").count() != 0:
            raise AssertionError("Sala de decisión volvió a exponer un botón visual muerto")
        if page.locator(".decision-action a[href='#reduccion']").count() != 1:
            raise AssertionError("Sala de decisión no conduce al bloque de reducción")
        if page.locator(".plan-table caption").inner_text().strip() == "":
            raise AssertionError("La comparación de planes perdió su caption accesible")

        page.locator('[data-preview-view="calidad"]').click()
        decision = page.locator('[data-preview-quality-decision]')
        page.locator('[data-preview-quality-action="improve"]').click()
        if "permanece abierto" not in decision.inner_text().lower():
            raise AssertionError("Solicitar mejora no produce un estado visible")
        page.locator('[data-preview-quality-action="accept"]').click()
        accepted = decision.inner_text().lower()
        if "aceptado con limitación" not in accepted or "justificación" not in accepted:
            raise AssertionError(f"Aceptar con limitación no conserva el truth lock: {accepted}")
        pressed = page.locator('[data-preview-quality-action="accept"]').get_attribute("aria-pressed")
        if pressed != "true":
            raise AssertionError("La decisión de calidad no expone estado aria-pressed")
        stored = page.evaluate("localStorage.getItem('cth-pages-preview-quality-decision')")
        if stored != "accept":
            raise AssertionError(f"La decisión de calidad no persiste localmente: {stored!r}")

        evidence = {
            "frameworks": observed,
            "structured_data": {"types": [item.get("@type") for item in schemas], "offers": offers},
            "semantic_actions": "ok",
            "quality_decision": stored,
        }
        (ARTIFACT_DIR / "site-authority-evidence.json").write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        context.close()
        browser.close()
        print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
