#!/usr/bin/env python3
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("Uso: copy_sqlite_database.py ORIGEN DESTINO", file=sys.stderr)
        return 2
    source = Path(sys.argv[1]).expanduser().resolve()
    target = Path(sys.argv[2]).expanduser().resolve()
    if not source.is_file():
        print(f"No existe la base de origen: {source}", file=sys.stderr)
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as source_db:
        integrity = source_db.execute("PRAGMA integrity_check").fetchone()
        if not integrity or integrity[0] != "ok":
            print(f"La base de origen no supera integrity_check: {integrity}", file=sys.stderr)
            return 1
        with sqlite3.connect(target) as target_db:
            source_db.backup(target_db)
            target_db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            target_db.commit()
    print(f"Copia SQLite consistente creada: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
