# V1.6.0 · Consolidación de `database.py`

## Hallazgo

`app/database.py` tiene 2.171 líneas, pero el problema actual no es que concentre todos los modelos o el engine.

La arquitectura ya separa correctamente:

- `app/db/base.py`: Base, engine, SessionLocal y rutas de almacenamiento;
- `app/db/models/*`: modelos ORM por grupos;
- `app/database.py`: fachada de compatibilidad + auditoría + progreso + defaults/seed + `init_db()`.

Por tanto, una reescritura de modelos sería innecesaria y riesgosa.

## Composición medida

`database.py` declara 41 funciones.

### Infraestructura/fachada

- `get_db`: 3 líneas
- `hash_password`: 2 líneas

### Auditoría

- `audit_event_digest`: 12 líneas
- `backfill_audit_chain`: 20 líneas
- `add_audit`: 37 líneas

### Helpers legacy

- `write_simple_pdf`: 22 líneas
- `source_expected_periods`: 6 líneas
- `refresh_progress`: 15 líneas

### Inicialización y datos por defecto

- `_seed_methodology`: 71 líneas
- `_seed_sector_templates`: 74 líneas
- `_ensure_v012_defaults` … `_ensure_v100_final_defaults`: múltiples bloques históricos
- `init_db`: **420 líneas**

La mayoría del peso restante pertenece a bootstrap/seed, no al acceso transaccional normal de la aplicación.

## Dependencias actuales

La fachada `app.database` sigue siendo un contrato muy usado:

- `get_db`: usado por al menos 27 archivos;
- `add_audit`: al menos 28 archivos;
- `refresh_progress`: al menos 8 archivos;
- `init_db`: al menos 10 scripts/módulos;
- `SessionLocal`: al menos 14 consumidores;
- `Base`: al menos 24 consumidores.

Esto descarta eliminar `app.database` en un solo cambio.

## Arquitectura objetivo

```text
app/
  db/
    base.py
    models/
    seed.py
    bootstrap.py
  audit.py
  progress.py
  database.py   # fachada temporal de compatibilidad
```

### `db/seed.py`

Debe concentrar:

- `_seed_methodology`;
- `_seed_sector_templates`;
- defaults históricos que todavía sean necesarios para demo/bootstrap.

### `db/bootstrap.py`

Debe concentrar:

- `init_db`;
- orquestación de creación/seed;
- registro explícito y ordenado de pasos de bootstrap.

### `audit.py`

Debe concentrar:

- `audit_event_digest`;
- `backfill_audit_chain`;
- `add_audit`.

### `progress.py`

Debe evaluar si `refresh_progress` pertenece a dominio inventario/workflow y moverlo al contexto correcto.

### `database.py`

Durante V1.6 permanece como facade:

```python
from .db.base import Base, ENGINE, SessionLocal, ...
from .db.models import *
from .db.bootstrap import init_db
from .audit import add_audit, audit_event_digest, backfill_audit_chain
```

Así los 20+ consumidores actuales no deben migrarse todos en el mismo PR.

## Corte D1 recomendado

Mover **solo auditoría** primero.

Razones:

- conjunto cohesivo;
- reglas claras;
- bajo impacto en Alembic;
- no toca seed;
- permite conservar reexports en `database.py`;
- pruebas de hash chain ya existentes pueden fijar paridad.

## Corte D2

Mover seeds/defaults históricos a `db/seed.py` sin cambiar orden ni contenido.

Requisito: base nueva + demo + acceptance certification deben producir el mismo estado.

## Corte D3

Extraer `init_db()` a `db/bootstrap.py` y convertirlo en una secuencia explícita de pasos.

Objetivo adicional: dejar de acumular futuros `_ensure_vXYZ_defaults` dentro de un único archivo. Los cambios de esquema corresponden a Alembic; bootstrap debe limitarse a datos/configuración necesarios y seed controlado.

## Regla Alembic

V1.6 no utilizará este refactor para cambiar nombres de tablas, columnas o relaciones.

- Alembic continúa como autoridad del esquema.
- El refactor de Python no debe generar una migración por sí mismo.
- Cualquier migración funcional futura será un cambio separado.

## Definition of Done

- `database.py` queda como facade delgada;
- `init_db` deja de tener 420 líneas monolíticas;
- seed y bootstrap tienen tests propios;
- audit chain conserva hashes y locking;
- base vacía llega al mismo Alembic head;
- demo seed sigue siendo idempotente;
- imports legacy permanecen compatibles durante V1.6;
- `audit_architecture.py --enforce` permanece verde y se reduce el ceiling de `database_lines` solo después del corte real.
