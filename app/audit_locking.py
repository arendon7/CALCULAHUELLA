from __future__ import annotations

import threading

from sqlalchemy import event, text
from sqlalchemy.orm import Session

_LOCKS_GUARD = threading.Lock()
_LOCKS: dict[int, threading.RLock] = {}


def _lock_for(organization_id: int) -> threading.RLock:
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(int(organization_id), threading.RLock())


def acquire_audit_chain_lock(session: Session, organization_id: int) -> None:
    """Serialize audit-chain writers until commit or rollback.

    PostgreSQL uses a transaction-scoped advisory lock across processes. SQLite
    uses a process lock, matching the single-process local distribution and
    preventing concurrent ASGI threads from forking the chain.
    """
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        session.execute(
            text("SELECT pg_advisory_xact_lock(:organization_id)"),
            {"organization_id": int(organization_id)},
        )
        return
    if dialect != "sqlite":
        return
    acquired_ids: set[int] = session.info.setdefault("audit_chain_lock_ids", set())
    if int(organization_id) in acquired_ids:
        return
    lock = _lock_for(int(organization_id))
    lock.acquire()
    acquired_ids.add(int(organization_id))
    session.info.setdefault("audit_chain_locks", []).append(lock)


@event.listens_for(Session, "after_transaction_end")
def _release_locks(session: Session, transaction) -> None:  # pragma: no cover - event lifecycle
    if transaction.parent is not None:
        return
    locks = session.info.pop("audit_chain_locks", [])
    session.info.pop("audit_chain_lock_ids", None)
    for lock in reversed(locks):
        try:
            lock.release()
        except RuntimeError:
            pass
