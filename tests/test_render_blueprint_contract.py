from pathlib import Path


BLUEPRINT = Path("render.yaml")
CONFIG = Path("app/config.py")
DOCKERFILE = Path("Dockerfile")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_render_staging_uses_canonical_runtime_environment_names() -> None:
    blueprint = _text(BLUEPRINT)
    config = _text(CONFIG)

    assert "- key: SESSION_SECRET\n        generateValue: true" in blueprint
    assert "- key: SEED_DEMO\n        value: \"true\"" in blueprint
    assert "- key: SESSION_HTTPS_ONLY\n        value: \"true\"" in blueprint
    assert "- key: TRUSTED_HOSTS" in blueprint
    assert "calcula-tu-huella-arendon7-preview.onrender.com" in blueprint

    assert "SECRET_KEY" not in blueprint
    assert "AUTO_SEED_DEMO" not in blueprint
    assert 'os.environ.get(\n        "SESSION_SECRET"' in config
    assert 'env_bool("SEED_DEMO"' in config
    assert 'env_list("TRUSTED_HOSTS"' in config


def test_render_staging_pins_certified_postgresql_major() -> None:
    blueprint = _text(BLUEPRINT)

    assert 'postgresMajorVersion: "17"' in blueprint
    assert "fromDatabase:" in blueprint
    assert "name: calcula-tu-huella-preview-db" in blueprint
    assert "property: connectionString" in blueprint


def test_render_staging_aligns_runtime_and_container_health_port() -> None:
    blueprint = _text(BLUEPRINT)
    dockerfile = _text(DOCKERFILE)

    assert "- key: PORT\n        value: \"8765\"" in blueprint
    assert "PORT=8765" in dockerfile
    assert "EXPOSE 8765" in dockerfile
    assert "127.0.0.1:8765/api/health" in dockerfile


def test_render_staging_remains_explicitly_non_production() -> None:
    blueprint = _text(BLUEPRINT)

    assert "- key: APP_ENV\n        value: staging" in blueprint
    assert "- key: DEPLOYMENT_STRICT\n        value: \"false\"" in blueprint
    assert "- key: SCHEDULER_ENABLED\n        value: \"false\"" in blueprint
    assert "- key: STORAGE_BACKEND\n        value: local" in blueprint
    assert "plan: free" in blueprint
