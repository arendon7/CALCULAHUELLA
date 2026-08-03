from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.engine import Engine

from .database import Base


class DatabaseTransferError(RuntimeError):
    pass


@dataclass
class TransferResult:
    source_backend: str
    target_backend: str
    table_counts: dict[str, int]
    copied_rows: int
    reconciled: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_backend": self.source_backend,
            "target_backend": self.target_backend,
            "table_counts": self.table_counts,
            "copied_rows": self.copied_rows,
            "reconciled": self.reconciled,
        }


def _backend(engine: Engine) -> str:
    return engine.url.get_backend_name()


def database_inventory(database_url: str) -> dict[str, int]:
    engine = create_engine(database_url, pool_pre_ping=True)
    inspector = inspect(engine)
    available = set(inspector.get_table_names())
    counts: dict[str, int] = {}
    with engine.connect() as connection:
        for table in Base.metadata.sorted_tables:
            if table.name in available:
                counts[table.name] = int(connection.execute(select(func.count()).select_from(table)).scalar_one())
    engine.dispose()
    return counts


def transfer_database(
    source_url: str,
    target_url: str,
    *,
    require_empty_target: bool = True,
    batch_size: int = 500,
) -> TransferResult:
    if source_url == target_url:
        raise DatabaseTransferError("La base origen y destino no pueden ser la misma.")
    source = create_engine(source_url, pool_pre_ping=True)
    target = create_engine(target_url, pool_pre_ping=True)
    source_tables = set(inspect(source).get_table_names())
    target_tables = set(inspect(target).get_table_names())
    expected = {table.name for table in Base.metadata.sorted_tables}
    missing_source = sorted(expected - source_tables)
    missing_target = sorted(expected - target_tables)
    if missing_source:
        raise DatabaseTransferError("La base origen no contiene todas las tablas: " + ", ".join(missing_source[:10]))
    if missing_target:
        raise DatabaseTransferError("La base destino no está migrada: " + ", ".join(missing_target[:10]))

    copied_rows = 0
    source_counts: dict[str, int] = {}
    with source.connect() as source_connection, target.begin() as target_connection:
        if require_empty_target:
            nonempty = []
            for table in Base.metadata.sorted_tables:
                count = int(target_connection.execute(select(func.count()).select_from(table)).scalar_one())
                if count:
                    nonempty.append(f"{table.name}={count}")
            if nonempty:
                raise DatabaseTransferError("La base destino debe estar vacía: " + ", ".join(nonempty[:10]))

        for table in Base.metadata.sorted_tables:
            rows = [dict(row) for row in source_connection.execute(select(table)).mappings()]
            source_counts[table.name] = len(rows)
            for offset in range(0, len(rows), max(1, batch_size)):
                batch = rows[offset:offset + max(1, batch_size)]
                if batch:
                    target_connection.execute(table.insert(), batch)
                    copied_rows += len(batch)

        if _backend(target).startswith("postgresql"):
            for table in Base.metadata.sorted_tables:
                pk_columns = list(table.primary_key.columns)
                if len(pk_columns) != 1:
                    continue
                column = pk_columns[0]
                if not getattr(column.type, "python_type", None) is int:
                    continue
                table_name = table.name.replace('"', '""')
                column_name = column.name.replace('"', '""')
                target_connection.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('\\\"{table_name}\\\"', '{column_name}'), "
                    f"COALESCE((SELECT MAX(\\\"{column_name}\\\") FROM \\\"{table_name}\\\"), 1), "
                    f"(SELECT COUNT(*) > 0 FROM \\\"{table_name}\\\"))"
                ))

        target_counts = {
            table.name: int(target_connection.execute(select(func.count()).select_from(table)).scalar_one())
            for table in Base.metadata.sorted_tables
        }
        if source_counts != target_counts:
            differences = [
                f"{name}: origen {source_counts.get(name, 0)} / destino {target_counts.get(name, 0)}"
                for name in sorted(set(source_counts) | set(target_counts))
                if source_counts.get(name, 0) != target_counts.get(name, 0)
            ]
            raise DatabaseTransferError("La reconciliación falló: " + "; ".join(differences[:10]))

    source.dispose()
    target.dispose()
    return TransferResult(
        source_backend=_backend(source),
        target_backend=_backend(target),
        table_counts=source_counts,
        copied_rows=copied_rows,
        reconciled=True,
    )
