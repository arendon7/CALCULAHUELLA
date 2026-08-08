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
from sqlalchemy import select

from app.database import SessionLocal, WorkItem, WorkItemEvent

BASE_URL = os.environ.get("HANDOFF_GATE_BASE_URL", "http://127.0.0.1:8767").rstrip("/")
ARTIFACT_DIR = Path(os.environ.get("HANDOFF_GATE_ARTIFACT_DIR", "handoff-gate-artifacts")).resolve()
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
PASSWORD = "Demo2026!"
TITLE = "Ensayo piloto E2E · relevo completo"

ACTORS = {
    "Administrador": "admin@calculatuhuella.local",
    "Cliente": "cliente@calculatuhuella.local",
    "Revisor": "revisor@calculatuhuella.local",
    "Verificador": "verificador@calculatuhuella.local",
}

STATUS_LABELS = {
    "assigned": "Asignada",
    "accepted_by_assignee": "Aceptada por responsable",
    "in_progress": "En preparación",
    "submitted": "Entregada",
    "validating": "En validación",
    "under_review": "En revisión",
    "accepted_by_reviewer": "Aceptada por revisor",
    "closed": "Cerrada",
}

EXPECTED_EVENTS = [
    ("created_and_assigned", "Administrador", ACTORS["Administrador"], "draft", "assigned"),
    ("accept_assignment", "Cliente", ACTORS["Cliente"], "assigned", "accepted_by_assignee"),
    ("start", "Cliente", ACTORS["Cliente"], "accepted_by_assignee", "in_progress"),
    ("submit", "Cliente", ACTORS["Cliente"], "in_progress", "submitted"),
    ("start_validation", "Revisor", ACTORS["Revisor"], "submitted", "validating"),
    ("send_to_review", "Revisor", ACTORS["Revisor"], "validating", "under_review"),
    ("accept_delivery", "Revisor", ACTORS["Revisor"], "under_review", "accepted_by_reviewer"),
    ("close", "Administrador", ACTORS["Administrador"], "accepted_by_reviewer", "closed"),
]


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


def _card(page: Page, item_id: int):
    card = page.locator(f"#tarea-{item_id}")
    card.wait_for(state="visible")
    return card


def _status(page: Page, item_id: int) -> str:
    return _card(page, item_id).locator(".status-badge").inner_text().strip()


def _assert_status(page: Page, item_id: int, status_code: str) -> None:
    expected = STATUS_LABELS[status_code]
    actual = _status(page, item_id)
    if actual != expected:
        raise AssertionError(f"Tarea #{item_id}: estado visual {actual!r}; esperado {expected!r}.")


def _screenshot(page: Page, name: str) -> str:
    page.evaluate(
        "document.querySelectorAll('dialog[open]').forEach(d => { try { d.close(); } catch (_) { d.removeAttribute('open'); } })"
    )
    path = ARTIFACT_DIR / name
    page.screenshot(path=str(path), full_page=True)
    return name


def _create_item(page: Page) -> int:
    page.goto(f"{BASE_URL}/mi-trabajo?scope=all", wait_until="networkidle")
    form = page.locator("form.work-create-form")
    form.wait_for(state="visible")
    form.locator('input[name="title"]').fill(TITLE)
    form.locator('select[name="work_type"]').select_option("data_request")
    form.locator('textarea[name="description"]').fill(
        "Ensayo controlado de relevo entre responsable, revisión y cierre antes del piloto humano."
    )
    form.locator('select[name="priority"]').select_option("high")
    form.locator('input[name="assignee_email"]').fill(ACTORS["Cliente"])
    form.locator('textarea[name="acceptance_criteria"]').fill(
        "La entrega debe quedar presentada, validada, revisada y cerrada con trazabilidad de cada actor."
    )
    form.locator('input[name="next_action"]').fill("Aceptar la asignación y preparar la entrega de ensayo.")
    form.locator('button[type="submit"]').click()
    page.wait_for_load_state("networkidle")

    card = page.locator("article.work-card").filter(has_text=TITLE).first
    card.wait_for(state="visible")
    raw_id = card.get_attribute("id") or ""
    if not raw_id.startswith("tarea-"):
        raise AssertionError(f"No se pudo recuperar el ID de la tarea creada: {raw_id!r}")
    item_id = int(raw_id.removeprefix("tarea-"))
    _assert_status(page, item_id, "assigned")
    return item_id


def _transition(page: Page, item_id: int, action: str, target_status: str, comment: str = "") -> None:
    page.goto(f"{BASE_URL}/mi-trabajo?scope=all", wait_until="networkidle")
    card = _card(page, item_id)
    form = card.locator(f'form.work-action-form:has(input[name="action"][value="{action}"])')
    if form.count() != 1:
        available = card.locator('form.work-action-form input[name="action"]').evaluate_all(
            "els => els.map(el => el.value)"
        )
        raise AssertionError(f"Tarea #{item_id}: acción {action!r} no disponible. Acciones={available}")
    comment_input = form.locator('input[name="comment"]')
    if comment_input.count() and comment:
        comment_input.fill(comment)
    form.locator('button[type="submit"]').click()
    page.wait_for_load_state("networkidle")
    _assert_status(page, item_id, target_status)


def _observer_contract(page: Page, item_id: int) -> None:
    page.goto(f"{BASE_URL}/mi-trabajo?scope=all", wait_until="networkidle")
    card = _card(page, item_id)
    _assert_status(page, item_id, "under_review")
    if card.locator("form.work-action-form").count() != 0:
        actions = card.locator('form.work-action-form input[name="action"]').evaluate_all("els => els.map(el => el.value)")
        raise AssertionError(f"Verificador no debe ejecutar transiciones operativas. Acciones={actions}")
    note = card.locator(".permission-note")
    if note.count() != 1:
        raise AssertionError("Verificador debe recibir una nota explícita de solo lectura sobre la tarea.")


def _persistence_contract(item_id: int) -> dict[str, object]:
    with SessionLocal() as session:
        item = session.get(WorkItem, item_id)
        if item is None:
            raise AssertionError(f"La tarea #{item_id} no existe en persistencia.")
        events = list(
            session.scalars(
                select(WorkItemEvent)
                .where(WorkItemEvent.work_item_id == item_id)
                .order_by(WorkItemEvent.id)
            )
        )
        actual = [
            (event.event_code, event.actor_role, event.actor_email, event.from_status_code, event.to_status_code)
            for event in events
        ]
        if actual != EXPECTED_EVENTS:
            raise AssertionError(f"Trazabilidad inesperada para tarea #{item_id}: {actual}")
        if item.status_code != "closed" or item.version != 8 or item.closed_at is None:
            raise AssertionError(
                f"Cierre persistido inválido: status={item.status_code}, version={item.version}, closed_at={item.closed_at}"
            )
        return {
            "item_id": item.id,
            "title": item.title,
            "status": item.status_code,
            "version": item.version,
            "closed_at": item.closed_at.isoformat() if item.closed_at else None,
            "events": [
                {
                    "event": event.event_code,
                    "actor_role": event.actor_role,
                    "actor_email": event.actor_email,
                    "from": event.from_status_code,
                    "to": event.to_status_code,
                    "comment": event.comment,
                }
                for event in events
            ],
        }


def main() -> int:
    evidence: dict[str, object] = {
        "engine": "chromium",
        "base_url": BASE_URL,
        "title": TITLE,
        "transitions": [],
        "screenshots": [],
    }
    browser_errors: dict[str, dict[str, list[str]]] = {}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        admin_context, admin, admin_console, admin_page_errors = _login(browser, "Administrador")
        client_context, client, client_console, client_page_errors = _login(browser, "Cliente")
        reviewer_context, reviewer, reviewer_console, reviewer_page_errors = _login(browser, "Revisor")
        verifier_context, verifier, verifier_console, verifier_page_errors = _login(browser, "Verificador")

        item_id = _create_item(admin)
        evidence["item_id"] = item_id
        evidence["screenshots"].append(_screenshot(admin, "01-asignada-administrador.png"))
        evidence["transitions"].append({"action": "create_and_assign", "actor": "Administrador", "status": "assigned"})

        _transition(client, item_id, "accept_assignment", "accepted_by_assignee")
        evidence["transitions"].append({"action": "accept_assignment", "actor": "Cliente", "status": "accepted_by_assignee"})
        _transition(client, item_id, "start", "in_progress")
        evidence["transitions"].append({"action": "start", "actor": "Cliente", "status": "in_progress"})
        evidence["screenshots"].append(_screenshot(client, "02-en-preparacion-cliente.png"))
        _transition(client, item_id, "submit", "submitted", "Entrega de ensayo preparada para validación.")
        evidence["transitions"].append({"action": "submit", "actor": "Cliente", "status": "submitted"})

        _transition(reviewer, item_id, "start_validation", "validating")
        evidence["transitions"].append({"action": "start_validation", "actor": "Revisor", "status": "validating"})
        _transition(reviewer, item_id, "send_to_review", "under_review")
        evidence["transitions"].append({"action": "send_to_review", "actor": "Revisor", "status": "under_review"})
        evidence["screenshots"].append(_screenshot(reviewer, "03-en-revision-revisor.png"))

        _observer_contract(verifier, item_id)
        evidence["screenshots"].append(_screenshot(verifier, "04-observacion-verificador.png"))
        evidence["verifier_observer"] = True

        _transition(reviewer, item_id, "accept_delivery", "accepted_by_reviewer")
        evidence["transitions"].append({"action": "accept_delivery", "actor": "Revisor", "status": "accepted_by_reviewer"})
        _transition(admin, item_id, "close", "closed")
        evidence["transitions"].append({"action": "close", "actor": "Administrador", "status": "closed"})
        evidence["screenshots"].append(_screenshot(admin, "05-cerrada-administrador.png"))

        evidence["persistence"] = _persistence_contract(item_id)

        browser_errors = {
            "Administrador": {"console": admin_console, "page": admin_page_errors},
            "Cliente": {"console": client_console, "page": client_page_errors},
            "Revisor": {"console": reviewer_console, "page": reviewer_page_errors},
            "Verificador": {"console": verifier_console, "page": verifier_page_errors},
        }
        evidence["browser_errors"] = browser_errors
        unexpected = {role: errors for role, errors in browser_errors.items() if errors["console"] or errors["page"]}
        if unexpected:
            raise AssertionError(f"Errores de navegador durante el relevo: {unexpected}")

        admin_context.close()
        client_context.close()
        reviewer_context.close()
        verifier_context.close()
        browser.close()

    evidence_path = ARTIFACT_DIR / "handoff-gate.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
