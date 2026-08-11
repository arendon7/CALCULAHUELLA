from __future__ import annotations

import sys as _sys
from pathlib import Path as _BootstrapPath

_PROJECT_ROOT = _BootstrapPath(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

import json
import os
from pathlib import Path

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright
from sqlalchemy import func, select

from app.database import (
    ActivityData,
    EmissionCalculation,
    EmissionSource,
    Inventory,
    InventoryDecision,
    ReportArtifact,
    ReviewObservation,
    SessionLocal,
    SupplierCampaign,
    SupplierDataRequest,
    SupplierResponse,
    VerificationFinding,
)

BASE_URL = os.environ.get("CLIMATE_GATE_BASE_URL", "http://127.0.0.1:8768").rstrip("/")
ARTIFACT_DIR = Path(os.environ.get("CLIMATE_GATE_ARTIFACT_DIR", "climate-gate-artifacts")).resolve()
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
PASSWORD = "Demo2026!"
INVENTORY_NAME = "Inventario corporativo 2025"
INTERNAL_OBSERVATION = "Completar cobertura anual de transporte contratado"
EXTERNAL_FINDING = "Trazabilidad incompleta del transporte contratado"

ACTORS = {
    "Administrador": "admin@calculatuhuella.local",
    "Consultor": "consultor@calculatuhuella.local",
    "Cliente": "cliente@calculatuhuella.local",
    "Revisor": "revisor@calculatuhuella.local",
    "Verificador": "verificador@calculatuhuella.local",
}

VALUES_BY_UNIT = {
    "L": 845.0,
    "t": 20.5,
    "t·km": 14250.0,
    "tCO₂e": 260.0,
    "kg": 12.0,
    "kWh": 19000.0,
}


def _login(browser: Browser, role: str) -> tuple[BrowserContext, Page, list[str], list[str]]:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    page.goto(f"{BASE_URL}/login", wait_until="networkidle")
    page.locator('input[name="email"]').fill(ACTORS[role])
    page.locator('input[name="password"]').fill(PASSWORD)
    page.locator("form.login-form button").click()
    page.wait_for_load_state("networkidle")
    if "/login" in page.url:
        raise AssertionError(f"{role}: el login demo no salió de /login.")
    page.evaluate(
        "window.localStorage.setItem('cth-tour-v14-' + document.body.dataset.role.toLowerCase().replaceAll(' ', '-'), 'completed')"
    )
    console_errors: list[str] = []
    page_errors: list[str] = []
    page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    return context, page, console_errors, page_errors


def _screenshot(page: Page, name: str) -> str:
    page.evaluate(
        "document.querySelectorAll('dialog[open]').forEach(d => { try { d.close(); } catch (_) { d.removeAttribute('open'); } })"
    )
    path = ARTIFACT_DIR / name
    page.screenshot(path=str(path), full_page=True)
    return name


def _capture_summary(page: Page) -> dict[str, object]:
    payload = page.evaluate(
        """async () => {
            const response = await fetch('/api/captura-guiada', {credentials: 'same-origin'});
            if (!response.ok) throw new Error(`captura API ${response.status}`);
            return await response.json();
        }"""
    )
    if not isinstance(payload, dict):
        raise AssertionError(f"Respuesta inesperada de captura guiada: {payload!r}")
    return payload


def _capture_pending_records(page: Page) -> list[dict[str, object]]:
    captured: list[dict[str, object]] = []
    for _ in range(36):
        summary = _capture_summary(page)
        pending = [item for item in summary["sources"] if item.get("next_start")]
        if not pending:
            uncovered = [
                str(item["name"])
                for item in summary["sources"]
                if float(item.get("coverage", 0)) < 100
            ]
            if float(summary["coverage"]) != 100 or uncovered:
                raise AssertionError(
                    f"Cobertura temporal inconsistente al finalizar captura: "
                    f"coverage={summary['coverage']}, uncovered={uncovered}"
                )
            return captured

        item = pending[0]
        source_id = int(item["id"])
        source_name = str(item["name"])
        unit = str(item["expected_unit"])
        value = VALUES_BY_UNIT.get(unit, 100.0)
        origin = "Información de proveedor" if unit == "tCO₂e" else "Registro operativo"

        page.goto(f"{BASE_URL}/captura-guiada?source_id={source_id}#registrar", wait_until="networkidle")
        form = page.locator("form[data-guided-capture-form]")
        form.wait_for(state="visible")
        form.locator('input[name="period_start"]').fill(str(item["next_start"]))
        form.locator('input[name="period_end"]').fill(str(item["next_end"]))
        form.locator('input[name="value"]').fill(str(value))
        form.locator('select[name="unit"]').select_option(unit)
        form.locator('select[name="data_origin"]').select_option(origin)
        form.locator("button.btn-primary").click()
        page.wait_for_load_state("networkidle")
        captured.append(
            {
                "source_id": source_id,
                "source": source_name,
                "period_start": item["next_start"],
                "period_end": item["next_end"],
                "value": value,
                "unit": unit,
                "origin": origin,
            }
        )
    raise AssertionError("La captura guiada no convergió a cobertura completa en 36 registros.")


def _open_details(container, summary_text: str):
    details = container.locator("details").filter(has_text=summary_text).first
    if details.count() != 1:
        raise AssertionError(f"No se encontró el bloque {summary_text!r}.")
    if not bool(details.evaluate("el => el.open")):
        details.locator("summary").click()
    return details


def _complete_supplier_chain(reviewer: Page) -> list[dict[str, object]]:
    with SessionLocal() as session:
        inventory = session.scalar(select(Inventory).where(Inventory.name == INVENTORY_NAME))
        if inventory is None:
            raise AssertionError(f"No existe {INVENTORY_NAME!r}.")
        requests = list(session.scalars(
            select(SupplierDataRequest)
            .join(SupplierCampaign)
            .where(SupplierCampaign.inventory_id == inventory.id)
            .order_by(SupplierDataRequest.id)
        ))
        pending = []
        for item in requests:
            response = session.scalar(select(SupplierResponse).where(SupplierResponse.request_id == item.id))
            if response is None or response.review_status != "Aprobado":
                pending.append({
                    "request_id": item.id,
                    "token": item.access_token,
                    "product_service": item.product_service,
                })

    completed: list[dict[str, object]] = []
    for index, item in enumerate(pending, 1):
        token = str(item["token"])
        reviewer.goto(f"{BASE_URL}/proveedor/responder/{token}", wait_until="networkidle")
        form = reviewer.locator("form#supplier-response-form")
        form.wait_for(state="visible")
        form.locator('select[name="method"]').select_option("Huella total suministrada")
        form.locator('input[name="reported_emissions_tco2e"]').fill(str(18.0 + index * 3.0))
        form.locator('input[name="methodology"]').fill("GHG Protocol Scope 3 · dato primario del proveedor")
        form.locator('textarea[name="boundary"]').fill(
            "Cradle-to-gate: materias primas, energía y producción hasta la puerta del proveedor; periodo 2025."
        )
        form.locator('textarea[name="notes"]').fill("Respuesta E2E V2.0 para completar la cadena de valor.")
        form.locator("button.btn-primary").click()
        reviewer.wait_for_load_state("networkidle")

        with SessionLocal() as session:
            response = session.scalar(
                select(SupplierResponse).where(SupplierResponse.request_id == int(item["request_id"]))
            )
            if response is None:
                raise AssertionError(f"La solicitud {item['request_id']} no persistió respuesta.")
            response_id = response.id

        reviewer.goto(f"{BASE_URL}/cadena-valor", wait_until="networkidle")
        review_form = reviewer.locator(f'form[action="/cadena-valor/respuestas/{response_id}/revisar"]')
        review_form.wait_for(state="attached")
        review_form.evaluate("el => { const d = el.closest('details'); if (d) d.open = true; }")
        review_form.locator('select[name="decision"]').select_option("Aprobado")
        review_form.locator('textarea[name="reviewer_comments"]').fill(
            "Metodología y límite documentados; respuesta aprobada para consolidación Scope 3 E2E."
        )
        review_form.locator("button").click()
        reviewer.wait_for_load_state("networkidle")
        completed.append({**item, "response_id": response_id, "decision": "Aprobado"})

    with SessionLocal() as session:
        inventory = session.scalar(select(Inventory).where(Inventory.name == INVENTORY_NAME))
        supplier_source = session.scalar(
            select(EmissionSource).where(
                EmissionSource.inventory_id == inventory.id,
                EmissionSource.category == "Datos específicos de proveedores",
            )
        )
        if supplier_source is None or supplier_source.progress != 100:
            raise AssertionError(
                f"La fuente consolidada de proveedores no quedó completa: "
                f"{getattr(supplier_source, 'progress', None)}"
            )
    return completed


def _close_internal_blocker(client: Page, reviewer: Page) -> None:
    client.goto(f"{BASE_URL}/control", wait_until="networkidle")
    card = client.locator("article.observation-item").filter(has_text=INTERNAL_OBSERVATION).first
    card.wait_for(state="visible")
    details = _open_details(card, "Responder o corregir")
    response_form = details.locator('form[action$="/responder"]')
    response_form.locator('textarea[name="response"]').fill(
        "Se completó la cobertura anual de transporte contratado con registros mensuales no estimados."
    )
    response_form.locator("button").click()
    client.wait_for_load_state("networkidle")

    card = client.locator("article.observation-item").filter(has_text=INTERNAL_OBSERVATION).first
    details = _open_details(card, "Responder o corregir")
    send_form = details.locator('form[action$="/enviar"]')
    send_form.locator("button").click()
    client.wait_for_load_state("networkidle")

    reviewer.goto(f"{BASE_URL}/control", wait_until="networkidle")
    card = reviewer.locator("article.observation-item").filter(has_text=INTERNAL_OBSERVATION).first
    card.wait_for(state="visible")
    details = _open_details(card, "Decisión del revisor")
    close_form = details.locator('form[action$="/cerrar"]')
    close_form.locator('textarea[name="resolution"]').fill(
        "Cobertura anual completada y cálculo recalculado; se cierra el hallazgo interno."
    )
    close_form.locator('select[name="decision"]').select_option("Cerrar")
    close_form.locator("button").click()
    reviewer.wait_for_load_state("networkidle")


def _assert_calculation_gate(page: Page) -> None:
    page.goto(f"{BASE_URL}/calculos", wait_until="networkidle")
    errors = page.locator("article.mini-card").filter(has_text="ERRORES").locator("strong").inner_text().strip()
    if errors != "0":
        raise AssertionError(f"Motor de cálculo reporta {errors} errores.")
    if page.locator(".calc-state.state-error").count():
        raise AssertionError("Existen fuentes con estado de cálculo en error.")


def _submit_review(page: Page) -> None:
    page.goto(f"{BASE_URL}/control", wait_until="networkidle")
    form = page.locator('form[action="/control/inventario/enviar-revision"]')
    form.wait_for(state="visible")
    form.locator('textarea[name="comments"]').fill("Cobertura completa y motor sin errores; iniciar revisión técnica E2E.")
    form.locator("button").click()
    page.wait_for_load_state("networkidle")


def _recommend(page: Page) -> None:
    page.goto(f"{BASE_URL}/control", wait_until="networkidle")
    if "Listo para aprobar" not in page.locator(".approval-panel").inner_text():
        with SessionLocal() as session:
            inventory = session.scalar(select(Inventory).where(Inventory.name == INVENTORY_NAME))
            source_state = [
                {"name": item.name, "category": item.category, "included": item.included, "progress": item.progress}
                for item in session.scalars(
                    select(EmissionSource).where(EmissionSource.inventory_id == inventory.id).order_by(EmissionSource.id)
                )
            ] if inventory else []
        raise AssertionError(
            f"Las puertas de calidad no quedaron listas: {page.locator('.approval-panel').inner_text()} | "
            f"Estado de fuentes: {source_state}"
        )
    form = page.locator('form[action="/control/inventario/recomendar"]')
    form.wait_for(state="visible")
    form.locator('textarea[name="comments"]').fill(
        "Revisión técnica favorable: cobertura completa, factores aprobados y cero errores de cálculo."
    )
    form.locator("button").click()
    page.wait_for_load_state("networkidle")


def _approve_inventory(page: Page) -> None:
    page.goto(f"{BASE_URL}/control", wait_until="networkidle")
    form = page.locator('form[action="/control/inventario/aprobar"]')
    form.wait_for(state="visible")
    form.locator('textarea[name="comments"]').fill(
        "Aprobación independiente posterior a recomendación técnica de un usuario diferente."
    )
    form.locator("button").click()
    page.wait_for_load_state("networkidle")
    if "Aprobado" not in page.locator(".page-head").inner_text():
        raise AssertionError("El inventario no quedó visualmente aprobado.")


def _generate_report(page: Page) -> None:
    page.goto(f"{BASE_URL}/reportes", wait_until="networkidle")
    form = page.locator('form[action="/reportes/generar"]').first
    form.wait_for(state="visible")
    form.locator("button").click()
    page.wait_for_load_state("networkidle")
    if page.locator("section.report-history tbody tr").count() < 1:
        raise AssertionError("No apareció el informe generado en el historial.")


def _approve_latest_report(page: Page) -> None:
    page.goto(f"{BASE_URL}/reportes", wait_until="networkidle")
    form = page.locator('section.report-history form[action$="/aprobar"]').first
    form.wait_for(state="visible")
    form.locator("button").click()
    page.wait_for_load_state("networkidle")
    first_status = page.locator("section.report-history tbody tr").first.locator(".status-chip").inner_text().strip()
    if first_status != "Aprobado":
        raise AssertionError(f"El último informe no quedó aprobado: {first_status!r}")


def _close_inventory(page: Page) -> None:
    page.goto(f"{BASE_URL}/control", wait_until="networkidle")
    form = page.locator('form[action="/control/inventario/cerrar"]')
    form.wait_for(state="visible")
    form.locator('textarea[name="comments"]').fill("Informe aprobado y expediente listo; cierre inmutable E2E V2.0.")
    form.locator("button").click()
    page.wait_for_load_state("networkidle")
    panel = page.locator(".approval-panel").inner_text()
    if "Inventario cerrado" not in panel:
        raise AssertionError(f"El inventario no quedó cerrado: {panel}")


def _close_external_finding(reviewer: Page, verifier: Page) -> None:
    reviewer.goto(f"{BASE_URL}/verificacion", wait_until="networkidle")
    card = reviewer.locator(".finding-card").filter(has_text=EXTERNAL_FINDING).first
    card.wait_for(state="visible")
    details = _open_details(card, "Responder")
    form = details.locator('form[action$="/responder"]')
    form.locator('textarea[name="management_response"]').fill(
        "Se completó el periodo anual y la revisión interna; los nuevos datos quedaron recalculados y aprobados."
    )
    form.locator("button").click()
    reviewer.wait_for_load_state("networkidle")

    verifier.goto(f"{BASE_URL}/verificacion", wait_until="networkidle")
    card = verifier.locator(".finding-card").filter(has_text=EXTERNAL_FINDING).first
    card.wait_for(state="visible")
    details = _open_details(card, "Decidir")
    form = details.locator('form[action$="/cerrar"]')
    form.locator('textarea[name="conclusion"]').fill(
        "La respuesta y la cobertura completa son suficientes para cerrar el hallazgo independiente."
    )
    form.locator('select[name="decision"]').select_option("Cerrar")
    form.locator("button").click()
    verifier.wait_for_load_state("networkidle")


def _generate_verification_package(page: Page) -> None:
    page.goto(f"{BASE_URL}/verificacion", wait_until="networkidle")
    form = page.locator('form[action="/verificacion/paquete"]')
    form.wait_for(state="visible")
    form.locator("button").click()
    page.wait_for_load_state("networkidle")
    if page.locator('a.download-row[href*="/reportes/"]').filter(has_text="ZIP").count() < 1:
        raise AssertionError("No apareció el paquete de verificación descargable.")


def _persistence_contract() -> dict[str, object]:
    with SessionLocal() as session:
        inventory = session.scalar(select(Inventory).where(Inventory.name == INVENTORY_NAME))
        if inventory is None:
            raise AssertionError(f"No existe {INVENTORY_NAME!r}.")
        sources = list(session.scalars(select(EmissionSource).where(EmissionSource.inventory_id == inventory.id)))
        incomplete = [source.name for source in sources if source.included and source.progress < 100]
        if incomplete:
            raise AssertionError(f"Fuentes incompletas después del journey: {incomplete}")
        error_count = session.scalar(
            select(func.count())
            .select_from(EmissionCalculation)
            .join(ActivityData)
            .join(EmissionSource)
            .where(EmissionSource.inventory_id == inventory.id, EmissionCalculation.status == "Error")
        ) or 0
        if error_count:
            raise AssertionError(f"Persisten {error_count} errores de cálculo.")
        observation = session.scalar(
            select(ReviewObservation).where(
                ReviewObservation.inventory_id == inventory.id,
                ReviewObservation.title == INTERNAL_OBSERVATION,
            )
        )
        if observation is None or observation.status != "Cerrada":
            raise AssertionError("La observación interna Mayor no quedó cerrada.")
        finding = session.scalar(
            select(VerificationFinding).where(
                VerificationFinding.inventory_id == inventory.id,
                VerificationFinding.title == EXTERNAL_FINDING,
            )
        )
        if finding is None or finding.status != "Cerrado":
            raise AssertionError("El hallazgo externo Mayor no quedó cerrado.")

        recommendation = session.scalar(
            select(InventoryDecision)
            .where(
                InventoryDecision.inventory_id == inventory.id,
                InventoryDecision.decision_type == "Revisión técnica",
                InventoryDecision.decision == "Recomendada",
            )
            .order_by(InventoryDecision.decided_at.desc())
        )
        approval = session.scalar(
            select(InventoryDecision)
            .where(
                InventoryDecision.inventory_id == inventory.id,
                InventoryDecision.decision_type == "Aprobación final",
                InventoryDecision.decision == "Aprobado",
            )
            .order_by(InventoryDecision.decided_at.desc())
        )
        if recommendation is None or approval is None or recommendation.decided_by == approval.decided_by:
            raise AssertionError("No se conservó la segregación entre recomendación y aprobación.")

        approved_report = session.scalar(
            select(ReportArtifact)
            .where(
                ReportArtifact.inventory_id == inventory.id,
                ReportArtifact.report_type != "Paquete de verificación",
                ReportArtifact.status == "Aprobado",
            )
            .order_by(ReportArtifact.generated_at.desc())
        )
        package = session.scalar(
            select(ReportArtifact)
            .where(
                ReportArtifact.inventory_id == inventory.id,
                ReportArtifact.report_type == "Paquete de verificación",
            )
            .order_by(ReportArtifact.generated_at.desc())
        )
        if approved_report is None:
            raise AssertionError("No existe un informe aprobado.")
        if package is None or not package.sha256:
            raise AssertionError("No existe paquete de verificación con SHA-256.")

        if inventory.status != "Cerrado" or not inventory.locked:
            raise AssertionError(f"Inventario final inválido: status={inventory.status}, locked={inventory.locked}")
        if inventory.approved_by != ACTORS["Administrador"] or inventory.closed_by != ACTORS["Administrador"]:
            raise AssertionError(
                f"Actores finales inesperados: approved_by={inventory.approved_by}, closed_by={inventory.closed_by}"
            )
        return {
            "inventory_id": inventory.id,
            "status": inventory.status,
            "locked": inventory.locked,
            "progress": inventory.progress,
            "source_progress": {source.name: source.progress for source in sources if source.included},
            "calculation_errors": int(error_count),
            "internal_observation": observation.status,
            "external_finding": finding.status,
            "recommended_by": recommendation.decided_by,
            "approved_by": approval.decided_by,
            "report": {
                "id": approved_report.id,
                "type": approved_report.report_type,
                "status": approved_report.status,
                "sha256": approved_report.sha256,
            },
            "verification_package": {
                "id": package.id,
                "status": package.status,
                "sha256": package.sha256,
            },
        }


def main() -> int:
    evidence: dict[str, object] = {
        "engine": "chromium",
        "base_url": BASE_URL,
        "inventory": INVENTORY_NAME,
        "capture_records": [],
        "screenshots": [],
    }

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        contexts: list[BrowserContext] = []
        errors: dict[str, dict[str, list[str]]] = {}
        pages: dict[str, Page] = {}
        for role in ("Administrador", "Consultor", "Cliente", "Revisor", "Verificador"):
            context, page, console_errors, page_errors = _login(browser, role)
            contexts.append(context)
            pages[role] = page
            errors[role] = {"console": console_errors, "page": page_errors}

        captured = _capture_pending_records(pages["Cliente"])
        evidence["capture_records"] = captured
        evidence["screenshots"].append(_screenshot(pages["Cliente"], "01-captura-completa.png"))

        supplier_responses = _complete_supplier_chain(pages["Revisor"])
        evidence["supplier_responses"] = supplier_responses
        evidence["screenshots"].append(_screenshot(pages["Revisor"], "01b-cadena-valor-completa.png"))

        _assert_calculation_gate(pages["Consultor"])
        evidence["screenshots"].append(_screenshot(pages["Consultor"], "02-calculo-sin-errores.png"))

        _close_internal_blocker(pages["Cliente"], pages["Revisor"])
        _submit_review(pages["Consultor"])
        _recommend(pages["Revisor"])
        evidence["screenshots"].append(_screenshot(pages["Revisor"], "03-recomendacion-tecnica.png"))

        _approve_inventory(pages["Administrador"])
        _generate_report(pages["Consultor"])
        _approve_latest_report(pages["Administrador"])
        _close_inventory(pages["Administrador"])
        evidence["screenshots"].append(_screenshot(pages["Administrador"], "04-inventario-cerrado.png"))

        _close_external_finding(pages["Revisor"], pages["Verificador"])
        _generate_verification_package(pages["Verificador"])
        evidence["screenshots"].append(_screenshot(pages["Verificador"], "05-paquete-verificacion.png"))

        evidence["persistence"] = _persistence_contract()
        evidence["browser_errors"] = errors
        unexpected = {role: item for role, item in errors.items() if item["console"] or item["page"]}
        if unexpected:
            raise AssertionError(f"Errores de navegador durante el journey climático: {unexpected}")

        for context in contexts:
            context.close()
        browser.close()

    evidence_path = ARTIFACT_DIR / "climate-journey-gate.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
