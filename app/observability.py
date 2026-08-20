from __future__ import annotations

import json
import math
import os
import re
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field

from .config import settings
from .path_privacy import privacy_safe_path


_RELEASE_COMMIT_PATTERN = re.compile(r"^[0-9a-fA-F]{7,64}$")


def release_commit_from_environment() -> str:
    """Return a public deploy identifier without exposing arbitrary environment data."""
    for key in ("RENDER_GIT_COMMIT", "GITHUB_SHA"):
        candidate = os.environ.get(key, "").strip()
        if _RELEASE_COMMIT_PATTERN.fullmatch(candidate):
            return candidate.lower()
    return ""


def _health_body_with_release_commit(body: bytes) -> bytes:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return body
    if not isinstance(payload, dict):
        return body
    payload["release_commit"] = release_commit_from_environment()
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


@dataclass
class MetricsRegistry:
    lock: threading.Lock = field(default_factory=threading.Lock)
    requests_total: dict[tuple[str, str, int], int] = field(default_factory=lambda: defaultdict(int))
    latencies: deque[float] = field(default_factory=lambda: deque(maxlen=2000))
    active_requests: int = 0
    errors_5xx: int = 0
    slow_requests: int = 0
    collapsed_series: int = 0

    def observe(self, method: str, path: str, status: int, duration: float) -> None:
        normalized = self._normalize_path(path)
        key = (method, normalized, status)
        with self.lock:
            if key not in self.requests_total and len(self.requests_total) >= settings.metrics_max_series:
                key = (method, "/__other__", status)
                self.collapsed_series += 1
            self.requests_total[key] += 1
            self.latencies.append(duration)
            if status >= 500:
                self.errors_5xx += 1
            if duration >= settings.slow_request_seconds:
                self.slow_requests += 1

    @staticmethod
    def _normalize_path(path: str) -> str:
        path = privacy_safe_path(path)
        pieces = []
        for piece in path.split("/"):
            if piece.isdigit() or (len(piece) > 20 and any(char.isdigit() for char in piece)):
                pieces.append(":id")
            else:
                pieces.append(piece)
        return "/".join(pieces) or "/"

    @staticmethod
    def _latency_summary(values: list[float]) -> tuple[float, float]:
        count = len(values)
        if not count:
            return 0.0, 0.0
        average = sum(values) / count
        # Nearest-rank p95, avoiding the former off-by-one behavior on short samples.
        p95_index = max(0, min(count - 1, math.ceil(count * 0.95) - 1))
        return average, values[p95_index]

    def snapshot(self) -> dict[str, object]:
        with self.lock:
            return self.snapshot_unlocked()

    def prometheus(self, version: str, environment: str) -> str:
        with self.lock:
            lines = [
                "# HELP cth_info Información de la aplicación.",
                "# TYPE cth_info gauge",
                f'cth_info{{version="{version}",environment="{environment}"}} 1',
                "# HELP cth_http_requests_total Solicitudes HTTP por método, ruta y estado.",
                "# TYPE cth_http_requests_total counter",
            ]
            for (method, path, status), value in sorted(self.requests_total.items()):
                escaped = path.replace('\\', '\\\\').replace('"', '\\"')
                lines.append(f'cth_http_requests_total{{method="{method}",path="{escaped}",status="{status}"}} {value}')
            snapshot = self.snapshot_unlocked()
            lines.extend([
                "# HELP cth_http_active_requests Solicitudes activas.",
                "# TYPE cth_http_active_requests gauge",
                f"cth_http_active_requests {snapshot['active_requests']}",
                "# HELP cth_http_errors_5xx_total Errores HTTP 5xx.",
                "# TYPE cth_http_errors_5xx_total counter",
                f"cth_http_errors_5xx_total {snapshot['errors_5xx']}",
                "# HELP cth_http_slow_requests_total Solicitudes que excedieron el umbral operativo.",
                "# TYPE cth_http_slow_requests_total counter",
                f"cth_http_slow_requests_total {snapshot['slow_requests']}",
                "# HELP cth_http_collapsed_series_total Series de alta cardinalidad consolidadas.",
                "# TYPE cth_http_collapsed_series_total counter",
                f"cth_http_collapsed_series_total {snapshot['collapsed_series']}",
                "# HELP cth_http_latency_average_seconds Latencia promedio reciente.",
                "# TYPE cth_http_latency_average_seconds gauge",
                f"cth_http_latency_average_seconds {snapshot['latency_average_seconds']}",
                "# HELP cth_http_latency_p95_seconds Latencia p95 reciente.",
                "# TYPE cth_http_latency_p95_seconds gauge",
                f"cth_http_latency_p95_seconds {snapshot['latency_p95_seconds']}",
            ])
            return "\n".join(lines) + "\n"

    def snapshot_unlocked(self) -> dict[str, object]:
        values = sorted(self.latencies)
        average, p95 = self._latency_summary(values)
        return {
            "request_count": sum(self.requests_total.values()),
            "active_requests": self.active_requests,
            "errors_5xx": self.errors_5xx,
            "slow_requests": self.slow_requests,
            "collapsed_series": self.collapsed_series,
            "series_count": len(self.requests_total),
            "latency_average_seconds": round(average, 6),
            "latency_p95_seconds": round(p95, 6),
        }


metrics = MetricsRegistry()


class OperationalMetricsMiddleware:
    """Pure ASGI metrics middleware with release identity on the health surface."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        started = time.perf_counter()
        status = 500
        path = str(scope.get("path", "/"))
        enrich_health = path == "/api/health"
        health_start = None
        health_body_parts: list[bytes] = []
        with metrics.lock:
            metrics.active_requests += 1

        async def send_with_status(message):
            nonlocal status, health_start
            message_type = message.get("type")
            if message_type == "http.response.start":
                status = int(message.get("status", 500))
                if enrich_health:
                    health_start = dict(message)
                    return
            if enrich_health and message_type == "http.response.body":
                health_body_parts.append(message.get("body", b""))
                if message.get("more_body", False):
                    return
                body = _health_body_with_release_commit(b"".join(health_body_parts))
                if health_start is not None:
                    headers = [
                        (name, value)
                        for name, value in health_start.get("headers", [])
                        if name.lower() != b"content-length"
                    ]
                    headers.append((b"content-length", str(len(body)).encode("ascii")))
                    health_start["headers"] = headers
                    await send(health_start)
                final_message = dict(message)
                final_message["body"] = body
                final_message["more_body"] = False
                await send(final_message)
                return
            await send(message)

        try:
            await self.app(scope, receive, send_with_status)
        finally:
            duration = time.perf_counter() - started
            with metrics.lock:
                metrics.active_requests = max(0, metrics.active_requests - 1)
            metrics.observe(str(scope.get("method", "GET")), path, status, duration)