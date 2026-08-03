from __future__ import annotations

import hashlib
import json
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import INSTANCE_DIR, settings
from .database import (
    DeploymentRehearsal,
    OperationalIncident,
    ReleaseCertification,
    RestoreDrill,
)
from .deployment_readiness import run_deployment_rehearsal
from .operations import create_backup, rehearse_backup_restore, verify_backup_archive
from .storage import storage

CERTIFICATION_DIR = INSTANCE_DIR / "certifications"
CERTIFICATION_DIR.mkdir(parents=True, exist_ok=True)


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _persist_restore_drill(
    session: Session,
    organization_id: int,
    performed_by: str,
    result: dict[str, object],
    notes: str,
) -> RestoreDrill:
    started_at = datetime.now(UTC)
    drill = RestoreDrill(
        organization_id=organization_id,
        backup_name=str(result.get("backup_name", "")),
        backup_sha256=str(result.get("backup_sha256", "")),
        application_version=str(result.get("application_version", "")),
        database_backend=str(result.get("database_backend", "")),
        status=str(result.get("status", "Fallido")),
        integrity_result=str(result.get("integrity_result", "")),
        table_count=int(result.get("table_count", 0) or 0),
        record_summary_json=json.dumps(result.get("record_summary", {}), ensure_ascii=False, sort_keys=True),
        checks_json=json.dumps(result.get("checks", {}), ensure_ascii=False, sort_keys=True),
        notes=(notes.strip() + ("\n" if notes.strip() and result.get("issues") else "") + "; ".join(result.get("issues", []))).strip(),
        performed_by=performed_by,
        started_at=started_at,
        completed_at=datetime.now(UTC),
        duration_ms=int(result.get("duration_ms", 0) or 0),
    )
    session.add(drill)
    session.flush()
    return drill


def _write_bundle(
    artifact: Path,
    certificate_payload: dict[str, object],
    backup_manifest: dict[str, object],
    restore_result: dict[str, object],
    deployment: DeploymentRehearsal,
) -> None:
    deployment_payload = {
        "id": deployment.id,
        "status": deployment.status,
        "score": deployment.score,
        "strict_mode": deployment.strict_mode,
        "environment": deployment.environment,
        "database_backend": deployment.database_backend,
        "storage_backend": deployment.storage_backend,
        "checks": json.loads(deployment.checks_json or "[]"),
        "blockers": json.loads(deployment.blockers_json or "[]"),
        "warnings": json.loads(deployment.warnings_json or "[]"),
        "performed_by": deployment.performed_by,
        "started_at": deployment.started_at.isoformat() if deployment.started_at else "",
        "completed_at": deployment.completed_at.isoformat() if deployment.completed_at else "",
        "duration_ms": deployment.duration_ms,
    }
    readme = (
        "Calcula tu Huella · evidencia de certificación operativa\n\n"
        "Este paquete documenta la versión, el respaldo, el ensayo de restauración, "
        "la puerta de despliegue y los hashes asociados. Una validación local no equivale "
        "a una certificación productiva.\n"
    )
    with zipfile.ZipFile(artifact, "w", zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("certificacion.json", json.dumps(certificate_payload, ensure_ascii=False, indent=2, sort_keys=True))
        bundle.writestr("respaldo_manifest.json", json.dumps(backup_manifest, ensure_ascii=False, indent=2, sort_keys=True))
        bundle.writestr("restauracion.json", json.dumps(restore_result, ensure_ascii=False, indent=2, sort_keys=True))
        bundle.writestr("despliegue.json", json.dumps(deployment_payload, ensure_ascii=False, indent=2, sort_keys=True))
        bundle.writestr("LEEME.txt", readme)


def resolve_certification_artifact(name: str) -> Path:
    candidate = (CERTIFICATION_DIR / Path(name).name).resolve()
    if candidate.parent != CERTIFICATION_DIR.resolve() or not candidate.is_file():
        raise FileNotFoundError(name)
    return candidate


def run_release_certification(
    session: Session,
    organization_id: int,
    performed_by: str,
    *,
    strict: bool = False,
    notes: str = "",
) -> ReleaseCertification:
    """Generate auditable evidence for the current release.

    Local scope proves the application, backup and restore workflow. Productive
    certification additionally requires strict readiness and replicated evidence
    in an external storage backend. No external dependency is marked as approved
    unless it was actually used and verified.
    """
    started_clock = time.perf_counter()
    started_at = datetime.now(UTC)
    scope = "Producción" if strict else "Local"

    backup = create_backup(created_by=performed_by, label=f"cert-v{settings.version}")
    backup_path = Path(backup["path"])
    backup_check = verify_backup_archive(backup_path)
    backup_manifest = dict(backup_check.get("manifest") or {})

    restore_result = rehearse_backup_restore(backup_path)
    restore_drill = _persist_restore_drill(
        session,
        organization_id,
        performed_by,
        restore_result,
        f"Certificación {scope.lower()} V{settings.version}",
    )

    deployment = run_deployment_rehearsal(
        session,
        organization_id,
        performed_by,
        strict=strict,
        notes=f"Certificación {scope.lower()} V{settings.version}. {notes}".strip(),
    )

    external_backup_key = ""
    backup_replicated = False
    replication_detail = "El alcance local no exige réplica externa."
    if settings.storage_backend in {"filesystem", "s3"}:
        try:
            external_backup_key = storage.put_file(
                f"operacion/backups/{backup_path.name}",
                backup_path,
                "application/zip",
            )
            replicated = storage.get_bytes(external_backup_key)
            backup_replicated = _sha256_bytes(replicated) == str(backup["sha256"])
            replication_detail = (
                f"Réplica verificada en {settings.storage_backend}: {external_backup_key}"
                if backup_replicated
                else "El hash de la réplica externa no coincide."
            )
        except Exception as exc:  # pragma: no cover - integración externa real
            replication_detail = str(exc)

    unresolved_critical = list(session.scalars(select(OperationalIncident).where(
        OperationalIncident.organization_id == organization_id,
        OperationalIncident.status != "Resuelto",
        OperationalIncident.severity.in_(["Crítica", "Critical", "critical"]),
    )))

    checks = [
        {
            "code": "backup_integrity",
            "label": "Integridad del respaldo",
            "ok": bool(backup_check.get("ok")),
            "critical": True,
            "detail": "; ".join(backup_check.get("issues", [])) or f"SHA-256 {backup['sha256']}",
        },
        {
            "code": "version_match",
            "label": "Versión del respaldo",
            "ok": str(backup_manifest.get("version", "")) == settings.version,
            "critical": True,
            "detail": f"Respaldo {backup_manifest.get('version', '')} / aplicación {settings.version}",
        },
        {
            "code": "restore_drill",
            "label": "Restauración aislada",
            "ok": bool(restore_result.get("ok")),
            "critical": True,
            "detail": f"{restore_result.get('status', '')} · {restore_result.get('integrity_result', '')}",
        },
        {
            "code": "deployment_gate",
            "label": "Puerta de despliegue",
            "ok": deployment.status == "Aprobado",
            "critical": True,
            "detail": f"{deployment.status} · {deployment.score}%",
        },
        {
            "code": "external_replication",
            "label": "Réplica externa del respaldo",
            "ok": backup_replicated,
            "critical": strict,
            "detail": replication_detail,
        },
        {
            "code": "critical_incidents",
            "label": "Incidentes críticos abiertos",
            "ok": not unresolved_critical,
            "critical": strict,
            "detail": f"{len(unresolved_critical)} incidentes críticos abiertos",
        },
    ]
    blockers = [item for item in checks if item["critical"] and not item["ok"]]
    core_ok = all(item["ok"] for item in checks if item["code"] in {"backup_integrity", "version_match", "restore_drill", "deployment_gate"})
    production_approved = strict and not blockers
    if production_approved:
        status = "Certificada"
    elif not strict and core_ok:
        status = "Validación local"
    else:
        status = "Bloqueada"

    evidence = {
        "application": settings.app_name,
        "application_version": settings.version,
        "scope": scope,
        "status": status,
        "production_approved": production_approved,
        "environment": settings.environment,
        "database_backend": settings.database_backend,
        "storage_backend": settings.storage_backend,
        "organization_id": organization_id,
        "performed_by": performed_by,
        "started_at": started_at.isoformat(),
        "completed_at": datetime.now(UTC).isoformat(),
        "backup": {
            "name": backup_path.name,
            "sha256": backup["sha256"],
            "size": backup["size"],
            "external_key": external_backup_key,
            "replicated": backup_replicated,
        },
        "artifact_replication": {
            "required": strict,
            "external_key": "",
            "verified": False,
            "detail": "Pendiente de generar el paquete final.",
        },
        "restore_drill_id": restore_drill.id,
        "deployment_rehearsal_id": deployment.id,
        "checks": checks,
        "blockers": blockers,
        "notes": notes.strip(),
    }

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    artifact = CERTIFICATION_DIR / f"certificacion_v{settings.version.replace('.', '_')}_{scope.lower()}_{stamp}.zip"

    def finalize_local_artifact() -> tuple[str, str]:
        evidence["status"] = status
        evidence["production_approved"] = production_approved
        evidence["blockers"] = blockers
        evidence["completed_at"] = datetime.now(UTC).isoformat()
        evidence_without_hash = dict(evidence)
        evidence_without_hash.pop("certificate_hash", None)
        digest = _sha256_bytes(_canonical(evidence_without_hash))
        evidence["certificate_hash"] = digest
        _write_bundle(artifact, evidence, backup_manifest, restore_result, deployment)
        return digest, _sha256_file(artifact)

    certificate_hash, artifact_sha256 = finalize_local_artifact()
    external_artifact_key = ""
    artifact_replicated = False
    artifact_replication_detail = "El alcance local no exige réplica externa."
    if settings.storage_backend in {"filesystem", "s3"}:
        try:
            external_artifact_key = storage.put_file(
                f"operacion/certificaciones/{artifact.name}",
                artifact,
                "application/zip",
            )
            artifact_replicated = _sha256_bytes(storage.get_bytes(external_artifact_key)) == artifact_sha256
            artifact_replication_detail = (
                f"Réplica verificada en {settings.storage_backend}: {external_artifact_key}"
                if artifact_replicated
                else "El hash de la evidencia externa no coincide."
            )
        except Exception as exc:  # pragma: no cover - integración externa real
            artifact_replication_detail = str(exc)

    if strict and not artifact_replicated:
        blockers.append({
            "code": "certificate_replication",
            "label": "Réplica externa del certificado",
            "ok": False,
            "critical": True,
            "detail": artifact_replication_detail,
        })
        production_approved = False
        status = "Bloqueada"

    evidence["artifact_replication"] = {
        "required": strict,
        "external_key": external_artifact_key,
        "verified": artifact_replicated,
        "detail": artifact_replication_detail,
    }
    certificate_hash, artifact_sha256 = finalize_local_artifact()

    # The final evidence is uploaded again because its hash includes the verified
    # replication result. The final copy must match the local artifact byte-for-byte.
    if settings.storage_backend in {"filesystem", "s3"}:
        try:
            external_artifact_key = storage.put_file(
                f"operacion/certificaciones/{artifact.name}",
                artifact,
                "application/zip",
            )
            final_matches = _sha256_bytes(storage.get_bytes(external_artifact_key)) == artifact_sha256
            if strict and not final_matches:
                production_approved = False
                status = "Bloqueada"
                blockers.append({
                    "code": "certificate_final_hash",
                    "label": "Hash final de la certificación",
                    "ok": False,
                    "critical": True,
                    "detail": "La copia externa final no coincide con el paquete local.",
                })
                evidence["artifact_replication"]["verified"] = False
                evidence["artifact_replication"]["detail"] = "La copia externa final no coincide con el paquete local."
                certificate_hash, artifact_sha256 = finalize_local_artifact()
        except Exception as exc:  # pragma: no cover - integración externa real
            if strict:
                production_approved = False
                status = "Bloqueada"
                blockers.append({
                    "code": "certificate_final_upload",
                    "label": "Publicación final de la certificación",
                    "ok": False,
                    "critical": True,
                    "detail": str(exc),
                })
                evidence["artifact_replication"]["verified"] = False
                evidence["artifact_replication"]["detail"] = str(exc)
                certificate_hash, artifact_sha256 = finalize_local_artifact()

    certification = ReleaseCertification(
        organization_id=organization_id,
        application_version=settings.version,
        scope=scope,
        status=status,
        production_approved=production_approved,
        certificate_hash=certificate_hash,
        artifact_name=artifact.name,
        artifact_sha256=artifact_sha256,
        external_artifact_key=external_artifact_key,
        backup_name=backup_path.name,
        backup_sha256=str(backup["sha256"]),
        external_backup_key=external_backup_key,
        restore_drill_id=restore_drill.id,
        deployment_rehearsal_id=deployment.id,
        evidence_json=json.dumps(evidence, ensure_ascii=False, sort_keys=True),
        blockers_json=json.dumps(blockers, ensure_ascii=False, sort_keys=True),
        notes=notes.strip(),
        performed_by=performed_by,
        started_at=started_at,
        completed_at=datetime.now(UTC),
        duration_ms=round((time.perf_counter() - started_clock) * 1000),
    )
    session.add(certification)
    session.flush()
    return certification


def latest_certification(session: Session, organization_id: int) -> ReleaseCertification | None:
    return session.scalar(select(ReleaseCertification).where(
        ReleaseCertification.organization_id == organization_id,
    ).order_by(ReleaseCertification.started_at.desc(), ReleaseCertification.id.desc()))
