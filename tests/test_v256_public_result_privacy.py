from __future__ import annotations

import asyncio
import json

from app.observability import MetricsRegistry
from app.path_privacy import PUBLIC_RESULT_CANONICAL_PATH, privacy_safe_path
from app.security import RequestContextMiddleware, SecurityHeadersMiddleware
from app.config import settings


TOKEN_WITHOUT_DIGITS = "OnlyLettersAnd_Underscores-NoDigitsTokenValue"
RESULT_PATH = f"/diagnostico/gracias/{TOKEN_WITHOUT_DIGITS}"


async def _headers_for(path: str) -> dict[str, str]:
    messages: list[dict] = []

    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok", "more_body": False})

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    middleware = SecurityHeadersMiddleware(app)
    await middleware(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": [],
            "client": ("127.0.0.1", 12345),
        },
        receive,
        send,
    )
    start = next(item for item in messages if item["type"] == "http.response.start")
    return {key.decode("latin-1"): value.decode("latin-1") for key, value in start["headers"]}


def _headers(path: str) -> dict[str, str]:
    return asyncio.run(_headers_for(path))


def test_v256_sensitive_path_authority_redacts_result_token_only() -> None:
    assert not any(char.isdigit() for char in TOKEN_WITHOUT_DIGITS)
    assert privacy_safe_path(RESULT_PATH) == PUBLIC_RESULT_CANONICAL_PATH
    assert privacy_safe_path("/diagnostico") == "/diagnostico"
    assert privacy_safe_path("/inventarios/123") == "/inventarios/123"


def test_v256_metrics_never_expose_raw_public_result_token() -> None:
    registry = MetricsRegistry()
    registry.observe("GET", RESULT_PATH, 200, 0.01)

    assert ("GET", PUBLIC_RESULT_CANONICAL_PATH, 200) in registry.requests_total
    exported = registry.prometheus("test", "test")
    assert TOKEN_WITHOUT_DIGITS not in exported
    assert PUBLIC_RESULT_CANONICAL_PATH in exported


def test_v256_structured_log_never_exposes_raw_public_result_token(tmp_path, monkeypatch) -> None:
    async def exercise() -> None:
        async def app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok", "more_body": False})

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            return None

        middleware = RequestContextMiddleware(app)
        middleware.log_dir = tmp_path
        middleware.log_path = tmp_path / "application.jsonl"
        await middleware(
            {
                "type": "http",
                "method": "GET",
                "path": RESULT_PATH,
                "headers": [],
                "client": ("127.0.0.1", 12345),
            },
            receive,
            send,
        )

    monkeypatch.setattr(settings, "structured_logging", True)
    asyncio.run(exercise())

    record = json.loads((tmp_path / "application.jsonl").read_text(encoding="utf-8"))
    assert record["path"] == PUBLIC_RESULT_CANONICAL_PATH
    assert TOKEN_WITHOUT_DIGITS not in json.dumps(record)


def test_v256_result_uses_no_referrer_without_changing_public_defaults() -> None:
    result_headers = _headers(RESULT_PATH)
    assert result_headers["referrer-policy"] == "no-referrer"
    assert result_headers["cache-control"] == "no-store"

    assert _headers("/")["referrer-policy"] == "strict-origin-when-cross-origin"
    assert _headers("/diagnostico")["referrer-policy"] == "strict-origin-when-cross-origin"
