from __future__ import annotations

import asyncio

from app.security import SecurityHeadersMiddleware


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


def test_v255_individual_diagnosis_result_is_no_store() -> None:
    headers = _headers("/diagnostico/gracias/token-publico")
    assert headers["cache-control"] == "no-store"


def test_v255_public_diagnosis_and_landing_keep_normal_cache_policy() -> None:
    assert "cache-control" not in _headers("/diagnostico")
    assert "cache-control" not in _headers("/")
