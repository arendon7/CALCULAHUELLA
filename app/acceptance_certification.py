from __future__ import annotations

import asyncio
import hashlib
import json
import math
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select

from .config import INSTANCE_DIR, settings
from .database import AppUser, Organization, OrganizationMembership, SessionLocal, init_db
from .main import app
from .operations import create_backup, rehearse_backup_restore
from .tenant_integrity import audit_chain_integrity, audit_tenant_integrity

ACCEPTANCE_DIR = INSTANCE_DIR / "certifications" / "acceptance"


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(0, math.ceil(percentile * len(ordered)) - 1)
    return round(ordered[rank], 2)


def _canonical(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _accessible_organizations(email: str) -> list[dict[str, Any]]:
    with SessionLocal() as session:
        user = session.scalar(select(AppUser).where(AppUser.email == email.lower(), AppUser.active.is_(True)))
        if not user:
            raise ValueError(f"No existe el usuario activo {email}.")
        rows = list(session.execute(
            select(Organization.id, Organization.name, Organization.trade_name, OrganizationMembership.role)
            .join(OrganizationMembership, OrganizationMembership.organization_id == Organization.id)
            .where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.active.is_(True),
            )
            .order_by(Organization.id)
        ))
    return [
        {"id": int(row.id), "name": row.name, "trade_name": row.trade_name or row.name, "role": row.role}
        for row in rows
    ]


def run_multi_organization_journeys(email: str, password: str) -> dict[str, Any]:
    """Run real authenticated journeys while changing the active company."""
    organizations = _accessible_organizations(email)
    journeys: list[dict[str, Any]] = []
    errors: list[str] = []
    paths = (
        "/dashboard",
        "/informacion",
        "/calculos",
        "/api/reduccion/resumen",
        "/api/cadena-valor/resumen",
        "/api/huella-producto",
        "/api/proyectos-mitigacion",
        "/api/aseguramiento",
        "/api/metodologia/tierras-remociones",
    )

    with TestClient(app) as client:
        login = client.post("/login", data={"email": email, "password": password}, follow_redirects=False)
        if login.status_code != 303:
            return {
                "ok": False,
                "organization_count": len(organizations),
                "journeys": [],
                "errors": [f"Inicio de sesión rechazado: HTTP {login.status_code}"],
            }

        for organization in organizations:
            switch = client.post(f"/portafolio/cambiar/{organization['id']}", follow_redirects=False)
            if switch.status_code != 303:
                errors.append(f"No fue posible activar {organization['trade_name']}: HTTP {switch.status_code}")
                continue
            for path in paths:
                started = time.perf_counter()
                response = client.get(path)
                duration_ms = round((time.perf_counter() - started) * 1000, 2)
                item = {
                    "organization_id": organization["id"],
                    "organization": organization["trade_name"],
                    "path": path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                }
                if response.status_code != 200:
                    item["error"] = response.text[:240]
                    errors.append(f"{organization['trade_name']} {path}: HTTP {response.status_code}")
                elif path == "/dashboard" and organization["trade_name"] not in response.text:
                    item["error"] = "La pantalla no identifica la organización activa."
                    errors.append(f"Dashboard sin contexto activo para {organization['trade_name']}")
                journeys.append(item)

        # Prove that membership is enforced, not merely that switching works.
        with SessionLocal() as session:
            isolated = Organization(
                name=f"Organización aislada certificación {datetime.now(UTC).timestamp()}",
                trade_name="Organización aislada",
                tax_id="CERT-ISOLATED",
                sector="Prueba",
                country="Colombia",
                department="Antioquia",
                city="Medellín",
                status="Activa",
            )
            session.add(isolated)
            session.commit()
            isolated_id = isolated.id
        denied = client.post(f"/portafolio/cambiar/{isolated_id}", follow_redirects=False)
        with SessionLocal() as session:
            isolated = session.get(Organization, isolated_id)
            if isolated:
                session.delete(isolated)
                session.commit()
        membership_enforced = denied.status_code == 403
        if not membership_enforced:
            errors.append(f"Cambio a organización no autorizada devolvió HTTP {denied.status_code}")

    durations = [float(item["duration_ms"]) for item in journeys]
    return {
        "ok": not errors and bool(organizations) and len(organizations) >= 2,
        "organization_count": len(organizations),
        "organizations": organizations,
        "membership_enforced": membership_enforced,
        "request_count": len(journeys),
        "p50_ms": _percentile(durations, 0.50),
        "p95_ms": _percentile(durations, 0.95),
        "max_ms": round(max(durations), 2) if durations else 0.0,
        "journeys": journeys,
        "errors": errors,
    }


async def _load_worker(
    worker_id: int,
    email: str,
    password: str,
    organization_ids: list[int],
    request_count: int,
) -> list[dict[str, Any]]:
    transport = httpx.ASGITransport(
        app=app,
        raise_app_exceptions=False,
        client=("testclient", 12000 + worker_id),
    )
    records: list[dict[str, Any]] = []
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", timeout=30.0) as client:
        login = await client.post("/login", data={"email": email, "password": password}, follow_redirects=False)
        if login.status_code != 303:
            return [{"worker": worker_id, "path": "/login", "status_code": login.status_code, "duration_ms": 0.0}]
        for index in range(request_count):
            organization_id = organization_ids[index % len(organization_ids)]
            if index % 4 == 0:
                await client.post(f"/portafolio/cambiar/{organization_id}", follow_redirects=False)
            path = ("/api/health", "/dashboard", "/api/reduccion/resumen", "/api/cadena-valor/resumen")[index % 4]
            started = time.perf_counter()
            response = await client.get(path)
            records.append({
                "worker": worker_id,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            })
    return records


async def _run_load_async(email: str, password: str, workers: int, requests_per_worker: int) -> list[dict[str, Any]]:
    organization_ids = [item["id"] for item in _accessible_organizations(email)]
    if not organization_ids:
        return []
    batches = await asyncio.gather(*[
        _load_worker(worker_id, email, password, organization_ids, requests_per_worker)
        for worker_id in range(workers)
    ])
    return [item for batch in batches for item in batch]


def run_concurrent_acceptance(
    email: str,
    password: str,
    *,
    workers: int = 4,
    requests_per_worker: int = 8,
    p95_limit_ms: float = 2500.0,
) -> dict[str, Any]:
    workers = max(1, min(int(workers), 16))
    requests_per_worker = max(1, min(int(requests_per_worker), 100))
    started = time.perf_counter()
    records = asyncio.run(_run_load_async(email, password, workers, requests_per_worker))
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    durations = [float(item["duration_ms"]) for item in records]
    failures = [item for item in records if int(item["status_code"]) != 200]
    p95_ms = _percentile(durations, 0.95)
    return {
        "ok": bool(records) and not failures and p95_ms <= p95_limit_ms,
        "workers": workers,
        "requests_per_worker": requests_per_worker,
        "request_count": len(records),
        "failure_count": len(failures),
        "p50_ms": _percentile(durations, 0.50),
        "p95_ms": p95_ms,
        "p95_limit_ms": p95_limit_ms,
        "max_ms": round(max(durations), 2) if durations else 0.0,
        "elapsed_ms": elapsed_ms,
        "requests_per_second": round((len(records) / max(elapsed_ms / 1000, 0.001)), 2),
        "failures": failures[:20],
    }


def run_acceptance_certification(
    email: str,
    password: str,
    *,
    workers: int = 4,
    requests_per_worker: int = 8,
    p95_limit_ms: float = 2500.0,
) -> dict[str, Any]:
    init_db()
    started = time.perf_counter()
    started_at = datetime.now(UTC)
    with SessionLocal() as session:
        tenant = audit_tenant_integrity(session)
        audit_chain = audit_chain_integrity(session)

    journeys = run_multi_organization_journeys(email, password)
    load = run_concurrent_acceptance(
        email,
        password,
        workers=workers,
        requests_per_worker=requests_per_worker,
        p95_limit_ms=p95_limit_ms,
    )
    backup = create_backup(created_by=email, label="aceptacion-iteracion-10")
    restore = rehearse_backup_restore(Path(backup["path"]))

    checks = {
        "tenant_integrity": bool(tenant.get("ok")),
        "audit_chain": bool(audit_chain.get("ok")),
        "multi_organization_journeys": bool(journeys.get("ok")),
        "concurrent_load": bool(load.get("ok")),
        "backup_restore": bool(restore.get("ok")),
    }
    payload: dict[str, Any] = {
        "application": settings.app_name,
        "application_version": settings.version,
        "certification": "Iteración 10 · aceptación local",
        "status": "Aprobada" if all(checks.values()) else "Bloqueada",
        "ok": all(checks.values()),
        "started_at": started_at.isoformat(),
        "completed_at": datetime.now(UTC).isoformat(),
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        "performed_by": email,
        "environment": settings.environment,
        "database_backend": settings.database_backend,
        "checks": checks,
        "tenant_integrity": tenant,
        "audit_chain": audit_chain,
        "multi_organization_journeys": journeys,
        "concurrent_load": load,
        "backup_restore": restore,
        "backup": {
            "name": backup["name"],
            "sha256": backup["sha256"],
            "size": backup["size"],
        },
        "limitations": [
            "La carga se ejecuta dentro del proceso ASGI local; no sustituye una prueba distribuida de red.",
            "La certificación no demuestra instalación nativa física en Windows 10/11 ni macOS externo.",
            "La aprobación productiva exige almacenamiento externo, TLS, PostgreSQL y controles de infraestructura definidos para producción.",
        ],
    }
    unsigned = dict(payload)
    payload["certificate_hash"] = hashlib.sha256(_canonical(unsigned)).hexdigest()
    ACCEPTANCE_DIR.mkdir(parents=True, exist_ok=True)
    artifact = ACCEPTANCE_DIR / f"aceptacion_iteracion_10_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
    artifact.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")
    payload["artifact"] = str(artifact)
    payload["artifact_sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
    return payload
