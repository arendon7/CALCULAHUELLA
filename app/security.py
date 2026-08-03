from __future__ import annotations

import contextvars
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
import zipfile
from datetime import UTC, datetime, timedelta
from email.utils import formatdate
from http.cookies import SimpleCookie
from io import BytesIO
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs

from starlette.datastructures import Headers
from starlette.responses import Response

from .config import INSTANCE_DIR, settings

PBKDF2_ITERATIONS = max(int(os.environ.get("PBKDF2_ITERATIONS", "390000")), 10_000)
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
CSRF_COOKIE = "cth_csrf"
CSRF_FIELD = "_csrf_token"
CSRF_HEADER = "x-csrf-token"
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,80}$")
_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("cth_request_id", default="")
_log_lock = threading.Lock()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    if encoded.startswith("pbkdf2_sha256$"):
        try:
            _, iterations, salt, expected = encoded.split("$", 3)
            digest = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("ascii"),
                int(iterations),
            ).hex()
            return hmac.compare_digest(digest, expected)
        except (ValueError, TypeError):
            return False
    legacy = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy, encoded)


def password_needs_upgrade(encoded: str) -> bool:
    return not encoded.startswith("pbkdf2_sha256$")


def get_request_id() -> str:
    return _request_id_var.get("")


def _client_ip(scope: dict) -> str:
    client = scope.get("client")
    return str(client[0]) if client else "unknown"


def _cookie_value(headers: Headers, name: str) -> str:
    raw = headers.get("cookie", "")
    if not raw:
        return ""
    cookie = SimpleCookie()
    try:
        cookie.load(raw)
    except Exception:
        return ""
    morsel = cookie.get(name)
    return morsel.value if morsel else ""


def _csrf_form_value(content_type: str, body: bytes) -> str:
    if not body:
        return ""
    if content_type.startswith("application/x-www-form-urlencoded"):
        values = parse_qs(body.decode("utf-8", errors="replace"), keep_blank_values=True)
        return values.get(CSRF_FIELD, [""])[0]
    if content_type.startswith("multipart/form-data"):
        # El token es corto y se inyecta como campo oculto en todos los formularios.
        pattern = rb'name="_csrf_token"\r\n(?:[^\r\n]*\r\n)*\r\n([^\r\n]+)'
        match = re.search(pattern, body[: min(len(body), 1024 * 1024)])
        return match.group(1).decode("utf-8", errors="replace") if match else ""
    return ""


def _cookie_header(token: str) -> bytes:
    parts = [f"{CSRF_COOKIE}={token}", "Path=/", "SameSite=Lax", "Max-Age=28800"]
    if settings.session_https_only:
        parts.append("Secure")
    return "; ".join(parts).encode("latin-1")


class CSRFMiddleware:
    """Double-submit cookie protection for browser form requests.

    API endpoints remain protected by their own API key/webhook signatures and are
    excluded from this browser-oriented control. TestClient is exempt so the
    historical test suite can exercise business rules independently.
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or not settings.csrf_enabled:
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        method = scope.get("method", "GET").upper()
        path = scope.get("path", "")
        client_ip = _client_ip(scope)
        token = _cookie_value(headers, CSRF_COOKIE)
        should_set_cookie = not token or len(token) < 24
        if should_set_cookie:
            token = secrets.token_urlsafe(32)

        body = b""
        replayed = False
        if method not in SAFE_METHODS and not path.startswith("/api/") and client_ip != "testclient":
            chunks: list[bytes] = []
            more = True
            while more:
                message = await receive()
                if message.get("type") != "http.request":
                    continue
                chunks.append(message.get("body", b""))
                more = bool(message.get("more_body"))
            body = b"".join(chunks)
            supplied = headers.get(CSRF_HEADER, "") or _csrf_form_value(headers.get("content-type", ""), body)
            if not supplied or not hmac.compare_digest(supplied, token):
                response = Response(
                    "Solicitud rechazada: token de seguridad ausente o inválido. Recarga la página e inténtalo nuevamente.",
                    status_code=403,
                    media_type="text/plain; charset=utf-8",
                )
                await response(scope, receive, send)
                return

            async def replay_receive():
                nonlocal replayed
                if replayed:
                    return {"type": "http.request", "body": b"", "more_body": False}
                replayed = True
                return {"type": "http.request", "body": body, "more_body": False}

            downstream_receive = replay_receive
        else:
            downstream_receive = receive

        async def send_with_cookie(message):
            if message.get("type") == "http.response.start" and should_set_cookie:
                mutable_headers = list(message.get("headers", []))
                mutable_headers.append((b"set-cookie", _cookie_header(token)))
                message["headers"] = mutable_headers
            await send(message)

        await self.app(scope, downstream_receive, send_with_cookie)


class RequestContextMiddleware:
    """Adds a correlation ID and writes privacy-conscious structured request logs."""

    def __init__(self, app) -> None:
        self.app = app
        self.log_dir = INSTANCE_DIR / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.log_dir / "application.jsonl"

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        incoming = headers.get("x-request-id", "")
        request_id = incoming if REQUEST_ID_PATTERN.match(incoming) else secrets.token_hex(12)
        token = _request_id_var.set(request_id)
        started = time.perf_counter()
        status_code = 500

        async def send_with_id(message):
            nonlocal status_code
            if message.get("type") == "http.response.start":
                status_code = int(message.get("status", 500))
                mutable_headers = list(message.get("headers", []))
                mutable_headers.append((b"x-request-id", request_id.encode("ascii")))
                message["headers"] = mutable_headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            path = str(scope.get("path", ""))
            record = {
                "timestamp": datetime.now(UTC).isoformat(),
                "request_id": request_id,
                "method": scope.get("method", ""),
                "path": path,
                "status": status_code,
                "duration_ms": elapsed_ms,
                "client_hash": hashlib.sha256(_client_ip(scope).encode("utf-8")).hexdigest()[:16],
            }
            if settings.structured_logging and not path.startswith("/static/"):
                line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
                try:
                    with _log_lock:
                        with self.log_path.open("a", encoding="utf-8") as handle:
                            handle.write(line)
                except OSError:
                    pass
            _request_id_var.reset(token)


class SecurityHeadersMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        async def send_headers(message):
            if message.get("type") == "http.response.start":
                headers = list(message.get("headers", []))
                existing = {key.lower() for key, _ in headers}
                additions = {
                    b"x-content-type-options": b"nosniff",
                    b"x-frame-options": b"DENY",
                    b"referrer-policy": b"strict-origin-when-cross-origin",
                    b"permissions-policy": b"camera=(), microphone=(), geolocation=(), payment=()",
                    b"content-security-policy": (
                        b"default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
                        b"font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
                    ),
                }
                path = str(scope.get("path", ""))
                if path.startswith("/login") or path.startswith("/api/"):
                    additions[b"cache-control"] = b"no-store"
                if settings.is_production and settings.session_https_only:
                    additions[b"strict-transport-security"] = b"max-age=31536000; includeSubDomains"
                for key, value in additions.items():
                    if key not in existing:
                        headers.append((key, value))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_headers)


class ThrottleStatus:
    def __init__(self, blocked: bool, retry_after: int = 0) -> None:
        self.blocked = blocked
        self.retry_after = retry_after


class PersistentLoginThrottle:
    """Database-backed login throttling that survives restarts."""

    @staticmethod
    def _key(email: str, ip: str) -> str:
        normalized = f"{email.strip().lower()}|{ip}"
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def status(self, email: str, ip: str) -> ThrottleStatus:
        from sqlalchemy import select
        from .database import LoginSecurityState, SessionLocal

        key = self._key(email, ip)
        now = datetime.now(UTC).replace(tzinfo=None)
        with SessionLocal() as session:
            row = session.scalar(select(LoginSecurityState).where(LoginSecurityState.key_hash == key))
            if not row:
                return ThrottleStatus(False, 0)
            if row.blocked_until and row.blocked_until > now:
                return ThrottleStatus(True, max(1, int((row.blocked_until - now).total_seconds())))
            if row.window_started_at and row.window_started_at < now - timedelta(seconds=settings.login_window_seconds):
                row.failure_count = 0
                row.window_started_at = now
            row.blocked_until = None
            session.commit()
            return ThrottleStatus(False, 0)

    def failure(self, email: str, ip: str) -> ThrottleStatus:
        from sqlalchemy import select
        from .database import LoginSecurityState, SessionLocal

        key = self._key(email, ip)
        now = datetime.now(UTC).replace(tzinfo=None)
        with SessionLocal() as session:
            row = session.scalar(select(LoginSecurityState).where(LoginSecurityState.key_hash == key))
            if not row:
                row = LoginSecurityState(key_hash=key, failure_count=0, window_started_at=now, updated_at=now)
                session.add(row)
            if not row.window_started_at or row.window_started_at < now - timedelta(seconds=settings.login_window_seconds):
                row.window_started_at = now
                row.failure_count = 0
            row.failure_count += 1
            row.updated_at = now
            if row.failure_count >= settings.login_attempts:
                row.blocked_until = now + timedelta(seconds=settings.login_block_seconds)
                row.failure_count = 0
                session.commit()
                return ThrottleStatus(True, settings.login_block_seconds)
            session.commit()
            return ThrottleStatus(False, 0)

    def success(self, email: str, ip: str) -> None:
        from sqlalchemy import delete
        from .database import LoginSecurityState, SessionLocal

        key = self._key(email, ip)
        with SessionLocal() as session:
            session.execute(delete(LoginSecurityState).where(LoginSecurityState.key_hash == key))
            session.commit()


login_throttle = PersistentLoginThrottle()


def security_state_snapshot() -> dict[str, object]:
    from sqlalchemy import func, select
    from .database import LoginSecurityState, SessionLocal

    now = datetime.now(UTC).replace(tzinfo=None)
    try:
        with SessionLocal() as session:
            active_blocks = session.scalar(
                select(func.count()).select_from(LoginSecurityState).where(LoginSecurityState.blocked_until > now)
            ) or 0
            tracked = session.scalar(select(func.count()).select_from(LoginSecurityState)) or 0
        return {"ok": True, "active_blocks": int(active_blocks), "tracked_keys": int(tracked)}
    except Exception as exc:
        return {"ok": False, "active_blocks": 0, "tracked_keys": 0, "detail": str(exc)}


DANGEROUS_PREFIXES = (
    b"MZ",  # Windows executable
    b"\x7fELF",  # Linux executable
    b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf",  # Mach-O
    b"#!/bin/", b"#!/usr/bin/",
)


def validate_upload_bytes(
    filename: str,
    content: bytes,
    content_type: str | None,
    allowed_extensions: Iterable[str],
) -> tuple[bool, str, str]:
    """Validate extension, signature and basic archive safety without executing content."""
    extension = Path(filename).suffix.lower()
    if extension not in set(allowed_extensions):
        return False, "Formato no permitido.", "application/octet-stream"
    if not content:
        return False, "El archivo está vacío.", "application/octet-stream"
    if any(content.startswith(prefix) for prefix in DANGEROUS_PREFIXES):
        return False, "El archivo contiene una firma ejecutable o de script no permitida.", "application/octet-stream"

    detected = "application/octet-stream"
    if extension == ".pdf":
        if not content.startswith(b"%PDF-"):
            return False, "El archivo no contiene una firma PDF válida.", detected
        detected = "application/pdf"
    elif extension == ".png":
        if not content.startswith(b"\x89PNG\r\n\x1a\n"):
            return False, "El archivo no contiene una firma PNG válida.", detected
        detected = "image/png"
    elif extension in {".jpg", ".jpeg"}:
        if not (content.startswith(b"\xff\xd8\xff") and content.rstrip().endswith(b"\xff\xd9")):
            return False, "El archivo no contiene una firma JPEG válida.", detected
        detected = "image/jpeg"
    elif extension == ".xlsx":
        if not content.startswith(b"PK"):
            return False, "El archivo no contiene una firma XLSX válida.", detected
        try:
            with zipfile.ZipFile(BytesIO(content)) as archive:
                names = archive.namelist()
                if len(names) > 2500:
                    return False, "El libro contiene demasiados componentes internos.", detected
                if any(name.startswith(("/", "\\")) or ".." in Path(name).parts for name in names):
                    return False, "El libro contiene rutas internas inseguras.", detected
                total_uncompressed = sum(info.file_size for info in archive.infolist())
                if total_uncompressed > max(100 * 1024 * 1024, len(content) * 120):
                    return False, "El libro excede los límites seguros de descompresión.", detected
                if "[Content_Types].xml" not in names:
                    return False, "La estructura XLSX está incompleta.", detected
        except zipfile.BadZipFile:
            return False, "El archivo XLSX está dañado.", detected
        detected = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif extension == ".xls":
        if not content.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
            return False, "El archivo no contiene una firma XLS válida.", detected
        detected = "application/vnd.ms-excel"
    elif extension == ".csv":
        if b"\x00" in content[:4096]:
            return False, "El CSV contiene datos binarios no permitidos.", detected
        try:
            content[: min(len(content), 1024 * 1024)].decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                content[: min(len(content), 1024 * 1024)].decode("latin-1")
            except UnicodeDecodeError:
                return False, "El CSV no tiene una codificación de texto reconocible.", detected
        detected = "text/csv"

    supplied = (content_type or "").lower().split(";", 1)[0]
    if supplied and supplied not in {"application/octet-stream", detected, "text/plain"}:
        # Safari y algunos navegadores usan tipos genéricos; una discrepancia clara se rechaza.
        if not (extension in {".jpg", ".jpeg"} and supplied == "image/jpg"):
            return False, "El tipo declarado por el navegador no coincide con el contenido del archivo.", detected
    return True, "Archivo válido.", detected
