from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


@dataclass
class MetricsRegistry:
    lock: threading.Lock = field(default_factory=threading.Lock)
    requests_total: dict[tuple[str, str, int], int] = field(default_factory=lambda: defaultdict(int))
    latencies: deque[float] = field(default_factory=lambda: deque(maxlen=2000))
    active_requests: int = 0
    errors_5xx: int = 0

    def observe(self, method: str, path: str, status: int, duration: float) -> None:
        normalized = self._normalize_path(path)
        with self.lock:
            self.requests_total[(method, normalized, status)] += 1
            self.latencies.append(duration)
            if status >= 500:
                self.errors_5xx += 1

    @staticmethod
    def _normalize_path(path: str) -> str:
        pieces = []
        for piece in path.split("/"):
            if piece.isdigit() or (len(piece) > 20 and any(char.isdigit() for char in piece)):
                pieces.append(":id")
            else:
                pieces.append(piece)
        return "/".join(pieces) or "/"

    def snapshot(self) -> dict[str, object]:
        with self.lock:
            values = sorted(self.latencies)
            count = len(values)
            average = sum(values) / count if count else 0.0
            p95 = values[min(count - 1, int(count * 0.95))] if count else 0.0
            return {
                "request_count": sum(self.requests_total.values()),
                "active_requests": self.active_requests,
                "errors_5xx": self.errors_5xx,
                "latency_average_seconds": round(average, 6),
                "latency_p95_seconds": round(p95, 6),
            }

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
        count = len(values)
        average = sum(values) / count if count else 0.0
        p95 = values[min(count - 1, int(count * 0.95))] if count else 0.0
        return {
            "request_count": sum(self.requests_total.values()),
            "active_requests": self.active_requests,
            "errors_5xx": self.errors_5xx,
            "latency_average_seconds": round(average, 6),
            "latency_p95_seconds": round(p95, 6),
        }


metrics = MetricsRegistry()


class OperationalMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        started = time.perf_counter()
        with metrics.lock:
            metrics.active_requests += 1
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            duration = time.perf_counter() - started
            with metrics.lock:
                metrics.active_requests = max(0, metrics.active_requests - 1)
            metrics.observe(request.method, request.url.path, status, duration)
