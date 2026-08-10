from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select

import app.inventory_context as inventory_context
import app.main as main_module
from app.accounting import is_gross_source
from app.db.base import SessionLocal
from app.db.models import EmissionSource, Inventory
from app.main import app

ROOT = Path(__file__).resolve().parents[1]


def _login(client: TestClient) -> None:
    response = client.post(
        "/login",
        data={"email": "admin@calculatuhuella.local", "password": "Demo2026!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_v160_inventory_context_has_dedicated_authority_and_compatible_facade_imports():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    context_source = (ROOT / "app/inventory_context.py").read_text(encoding="utf-8")
    for name in ("get_inventory", "inventory_metrics", "ensure_inventory_editable", "get_source_for_user"):
        assert f"def {name}(" not in main_source
        assert f"def {name}(" in context_source
        assert getattr(main_module, name) is getattr(inventory_context, name)
    assert "from .db.models import" in context_source
    assert "from .main import" not in context_source
    assert "from .database import" not in context_source


def test_v160_inventory_and_source_access_remain_scoped_to_active_organization():
    with SessionLocal() as session:
        inventory = session.scalar(select(Inventory).order_by(Inventory.id))
        source = session.scalar(select(EmissionSource).order_by(EmissionSource.id))
        assert inventory is not None
        assert source is not None

        user = {"organization_id": inventory.organization_id}
        loaded = inventory_context.get_inventory(session, user, inventory.id)
        assert loaded.id == inventory.id
        assert loaded.organization_id == inventory.organization_id

        foreign_user = {"organization_id": int(inventory.organization_id) + 999999}
        with pytest.raises(HTTPException) as inventory_error:
            inventory_context.get_inventory(session, foreign_user, inventory.id)
        assert inventory_error.value.status_code == 404
        assert inventory_error.value.detail == "Inventario no encontrado"

        source_inventory = session.get(Inventory, source.inventory_id)
        assert source_inventory is not None
        source_user = {"organization_id": source_inventory.organization_id}
        loaded_source = inventory_context.get_source_for_user(session, source_user, source.id)
        assert loaded_source.id == source.id
        foreign_source_user = {"organization_id": int(source_inventory.organization_id) + 999999}
        with pytest.raises(HTTPException) as source_error:
            inventory_context.get_source_for_user(session, foreign_source_user, source.id)
        assert source_error.value.status_code == 404
        assert source_error.value.detail == "Fuente no encontrada"


def test_v160_inventory_editability_contract_is_unchanged():
    inventory_context.ensure_inventory_editable(SimpleNamespace(locked=False, status="Borrador"))
    for candidate in (
        SimpleNamespace(locked=True, status="Borrador"),
        SimpleNamespace(locked=False, status="Cerrado"),
    ):
        with pytest.raises(HTTPException) as error:
            inventory_context.ensure_inventory_editable(candidate)
        assert error.value.status_code == 409
        assert "cerrado e inmutable" in error.value.detail


def test_v160_inventory_metrics_preserve_existing_semantics():
    with SessionLocal() as session:
        inventory = session.scalar(select(Inventory).order_by(Inventory.id))
        assert inventory is not None
        loaded = inventory_context.get_inventory(
            session, {"organization_id": inventory.organization_id}, inventory.id
        )
        metrics = inventory_context.inventory_metrics(loaded)
        included = [source for source in loaded.sources if is_gross_source(source)]
        assert metrics["total"] == round(sum(source.emissions for source in included), 1)
        assert metrics["scopes"] == {
            scope: round(sum(source.emissions for source in included if source.scope == scope), 1)
            for scope in (1, 2, 3)
        }
        assert len(metrics["monthly_series"]) == 12
        assert {item["month"] for item in metrics["monthly_series"]} == {
            "Ene", "Feb", "Mar", "Abr", "May", "Jun",
            "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
        }


def test_v160_inventory_routes_still_use_extracted_context():
    with TestClient(app) as client:
        _login(client)
        inventories = client.get("/inventarios")
        alias = client.get("/inventario", follow_redirects=False)
        assert inventories.status_code == 200
        assert alias.status_code == 303
        detail = client.get(alias.headers["location"])
        assert detail.status_code == 200
