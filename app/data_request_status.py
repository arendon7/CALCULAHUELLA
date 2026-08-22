from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, TypeVar


# El flujo actual persiste "Completado". Conservamos variantes históricas para
# que registros previos no reaparezcan como trabajo abierto en vistas operativas.
CLOSED_DATA_REQUEST_STATUSES = frozenset({"Completado", "Completada", "Cerrado", "Cerrada"})


class _HasStatus(Protocol):
    status: str


TRequest = TypeVar("TRequest", bound=_HasStatus)


def is_data_request_open(status: str | None) -> bool:
    return (status or "").strip() not in CLOSED_DATA_REQUEST_STATUSES


def open_data_requests(items: Iterable[TRequest]) -> list[TRequest]:
    return [item for item in items if is_data_request_open(item.status)]
