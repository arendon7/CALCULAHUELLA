from __future__ import annotations

import json
import os
import time
from pathlib import Path
from urllib.parse import urljoin

import httpx

BASE_URL = os.environ.get(
    "STAGING_BASE_URL",
    "https://calcula-tu-huella-arendon7-preview.onrender.com",
).rstrip("/")
PASSWORD = os.environ.get("STAGING_DEMO_PASSWORD", "Demo2026!")
ARTIFACT_DIR = Path(os.environ.get("REMOTE_UAT_ARTIFACT_DIR", "remote-auth-uat-artifacts")).resolve()
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
EVIDENCE_PATH = ARTIFACT_DIR / "authenticated-uat-evidence.json"
TIMEOUT = float(os.environ.get("REMOTE_UAT_REQUEST_TIMEOUT_SECONDS", "25"))

USERS = {
    "Administrador": "admin@calculatuhuella.local",
    "Consultor": "consultor@calculatuhuella.local",
    "Cliente": "cliente@calculatuhuella.local",
    "Revisor": "revisor@calculatuhuella.local",
    "Verificador": "verificador@calculatuhuella.local",
}


def csrf(client: httpx.Client, path: str = "/login") -> str:
    response = client.get(path)
    if response.status_code not in {200, 303}:
        raise AssertionError(f"No fue posible preparar CSRF desde {path}: {response.status_code}")
    token = client.cookies.get("cth_csrf")
    if not token or len(token) < 24:
        raise AssertionError("No se emitió cookie CSRF válida")
    return str(token)


def login(email: str) -> tuple[httpx.Client, str]:
    client = httpx.Client(base_url=BASE_URL, timeout=TIMEOUT, follow_redirects=False)
    token = csrf(client)
    response = client.post(
        "/login",
        data={"email": email, "password": PASSWORD},
        headers={"x-csrf-token": token},
    )
    if response.status_code != 303:
        raise AssertionError(f"Login de {email} falló: {response.status_code} {response.text[:300]}")
    location = response.headers.get("location", "")
    if not location.startswith("/"):
        raise AssertionError(f"Redirect de login inesperado para {email}: {location!r}")
    landing = client.get(location)
    if landing.status_code != 200:
        raise AssertionError(f"Destino autenticado {location} de {email} respondió {landing.status_code}")
    summary = client.get("/api/soporte/resumen")
    if summary.status_code != 200:
        raise AssertionError(f"Sesión de {email} no accede a API autenticada: {summary.status_code}")
    return client, location


def main() -> None:
    evidence: dict[str, object] = {
        "base_url": BASE_URL,
        "contract": "authenticated-uat-v1",
        "roles": {},
    }

    # 1. Cada rol debe poder establecer una sesión real y alcanzar su destino canónico.
    for role, email in USERS.items():
        client, location = login(email)
        expected = "/verificacion" if role == "Verificador" else "/dashboard"
        if location != expected:
            raise AssertionError(f"{role} redirigió a {location}, esperado {expected}")
        evidence["roles"][role] = {"email": email, "redirect": location, "authenticated_api": 200}
        client.close()

    # 2. Cliente crea un caso UAT único en la base aislada de Render.
    marker = f"UAT online persistencia {int(time.time())}"
    description = "Caso sintético creado por la certificación UAT online para validar persistencia y relevo entre actores."
    client, _ = login(USERS["Cliente"])
    token = str(client.cookies.get("cth_csrf") or csrf(client, "/soporte"))
    created = client.post(
        "/soporte/nuevo",
        data={
            "subject": marker,
            "description": description,
            "category": "Soporte funcional",
            "request_type": "Consulta",
            "priority": "Normal",
            "desired_outcome": "Validar persistencia entre sesiones y relevo cliente-consultor.",
        },
        headers={"x-csrf-token": token},
    )
    if created.status_code != 303:
        raise AssertionError(f"Creación del caso UAT falló: {created.status_code} {created.text[:300]}")
    ticket_path = created.headers.get("location", "")
    if not ticket_path.startswith("/soporte/"):
        raise AssertionError(f"Redirect del caso UAT inesperado: {ticket_path!r}")
    ticket_page = client.get(ticket_path)
    if ticket_page.status_code != 200 or marker not in ticket_page.text:
        raise AssertionError("El caso UAT no quedó visible para el cliente inmediatamente después de crearlo")
    client.close()

    # 3. Nueva sesión de Consultor: el caso debe persistir y permitir relevo.
    consultor, _ = login(USERS["Consultor"])
    persisted = consultor.get(ticket_path)
    if persisted.status_code != 200 or marker not in persisted.text:
        raise AssertionError("El caso UAT no persistió al abrir una sesión nueva de Consultor")
    consultor_token = str(consultor.cookies.get("cth_csrf") or csrf(consultor, ticket_path))
    response_text = "Respuesta UAT del consultor: caso recibido y trazabilidad entre actores confirmada."
    replied = consultor.post(
        f"{ticket_path}/mensajes",
        data={
            "body": response_text,
            "message_type": "Respuesta técnica",
            "visible_to_client": "on",
            "next_status": "En gestión",
        },
        headers={"x-csrf-token": consultor_token},
    )
    if replied.status_code != 303:
        raise AssertionError(f"Respuesta del Consultor falló: {replied.status_code} {replied.text[:300]}")
    consultor.close()

    # 4. Tercera sesión limpia de Cliente: debe ver respuesta persistida del Consultor.
    client2, _ = login(USERS["Cliente"])
    handoff = client2.get(ticket_path)
    if handoff.status_code != 200 or marker not in handoff.text or response_text not in handoff.text:
        raise AssertionError("El relevo Consultor→Cliente no persistió entre sesiones")
    client2.close()

    # 5. Consultor cierra el caso con resolución UAT para dejar el staging ordenado y auditable.
    consultor2, _ = login(USERS["Consultor"])
    close_token = str(consultor2.cookies.get("cth_csrf") or csrf(consultor2, ticket_path))
    closed = consultor2.post(
        f"{ticket_path}/actualizar",
        data={
            "status": "Cerrado",
            "assigned_to": "Equipo Calcula tu Huella",
            "priority": "Normal",
            "due_date": "",
            "resolution": "UAT online completada: persistencia entre sesiones y relevo cliente-consultor verificados.",
        },
        headers={"x-csrf-token": close_token},
    )
    if closed.status_code != 303:
        raise AssertionError(f"Cierre controlado del caso UAT falló: {closed.status_code} {closed.text[:300]}")
    final_page = consultor2.get(ticket_path)
    if final_page.status_code != 200 or "UAT online completada" not in final_page.text:
        raise AssertionError("La resolución final del caso UAT no quedó persistida")
    consultor2.close()

    evidence["persistence"] = {
        "ticket_path": ticket_path,
        "subject": marker,
        "created_by": USERS["Cliente"],
        "replied_by": USERS["Consultor"],
        "verified_again_by": USERS["Cliente"],
        "final_status": "Cerrado",
        "fresh_sessions": 4,
        "database": "Render PostgreSQL UAT aislado",
    }
    EVIDENCE_PATH.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
