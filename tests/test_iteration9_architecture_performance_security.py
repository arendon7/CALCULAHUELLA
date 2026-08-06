from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.observability import MetricsRegistry, OperationalMetricsMiddleware
from app.security import secure_secret_matches


@pytest.mark.smoke
def test_iteration9_direct_pytest_configuration_is_self_contained():
    root = Path(__file__).resolve().parents[1]
    config = (root / "pytest.ini").read_text(encoding="utf-8")
    assert "pythonpath = ." in config
    assert "testpaths = tests" in config


@pytest.mark.smoke
def test_iteration9_historical_tests_no_longer_rebuild_demo_database():
    root = Path(__file__).resolve().parent
    offenders = []
    for path in root.glob("test_*.py"):
        if path.name == Path(__file__).name:
            continue
        text = path.read_text(encoding="utf-8")
        if "Base.metadata.drop_all(ENGINE)\n    init_db()" in text:
            offenders.append(path.name)
    assert offenders == []


@pytest.mark.smoke
def test_iteration9_security_headers_and_sensitive_cache_policy():
    with TestClient(app) as client:
        response = client.get("/login")
    assert response.status_code == 200
    assert response.headers["cross-origin-opener-policy"] == "same-origin"
    assert response.headers["cross-origin-resource-policy"] == "same-origin"
    assert response.headers["x-permitted-cross-domain-policies"] == "none"
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.smoke
def test_iteration9_global_request_body_limit_rejects_before_parsing():
    original = settings.max_request_mb
    try:
        object.__setattr__(settings, "max_request_mb", 1)
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/activity-data",
                content=b"x" * (1024 * 1024 + 1),
                headers={"content-type": "application/json", "x-api-key": "invalid"},
            )
        assert response.status_code == 413
        assert "tamaño máximo" in response.text
    finally:
        object.__setattr__(settings, "max_request_mb", original)


@pytest.mark.smoke
def test_iteration9_secret_comparison_requires_configured_value():
    assert secure_secret_matches("same", "same") is True
    assert secure_secret_matches("different", "same") is False
    assert secure_secret_matches("", "") is False
    assert secure_secret_matches(None, "secret") is False


@pytest.mark.smoke
def test_iteration9_metrics_cardinality_is_bounded_and_middleware_is_pure_asgi():
    original = settings.metrics_max_series
    try:
        object.__setattr__(settings, "metrics_max_series", 2)
        registry = MetricsRegistry()
        registry.observe("GET", "/uno", 200, 0.01)
        registry.observe("GET", "/dos", 200, 0.02)
        registry.observe("GET", "/tres", 200, 0.03)
        snapshot = registry.snapshot()
        assert snapshot["series_count"] == 3  # two originals plus the bounded __other__ bucket
        assert snapshot["collapsed_series"] == 1
        assert registry.requests_total[("GET", "/__other__", 200)] == 1
        assert not hasattr(OperationalMetricsMiddleware, "dispatch")
    finally:
        object.__setattr__(settings, "metrics_max_series", original)
