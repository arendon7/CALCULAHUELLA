# V1.6-D1 · Validación de extracción de auditoría

## Estado

**Validado localmente · pendiente de materialización atómica en GitHub**

Parche reproducible:

`docs/architecture/patches/V1_6_D1_AUDIT_EXTRACTION_VALIDATED.patch`

## Precondición

El `app/database.py` local usado para el corte tiene Git blob SHA:

`7dac56f0142e405d29511fb56879177f2c296bc6`

Coincide con el blob de `database.py` en la rama V1.6 al diseñar D1.

## Cambio

Mover a `app/audit.py`:

- `audit_event_digest`;
- `backfill_audit_chain`;
- `add_audit`.

`app/database.py` conserva reexports:

```python
from .audit import add_audit, audit_event_digest, backfill_audit_chain
```

Por tanto, consumidores históricos como:

```python
from app.database import add_audit
```

no necesitan migrar en D1.

## Métricas

Antes:

- `database.py`: 2.171 líneas.

Después:

- `database.py`: **2.096 líneas**;
- `audit.py`: 84 líneas.

Git blob SHA del `database.py` modificado:

`25584650d271dd47ec620224f73da751b6d1bd55`

Git blob SHA de `audit.py`:

`e22da5b7a393ad33cf7288c8d7495d958140a1f0`

## Evidencia de pruebas

### Seguridad/auditoría dirigida

```text
7 passed in 6.06s
```

Ejecutado:

`tests/test_v024_security_hardening.py`

Incluye cadena de auditoría y endurecimiento de seguridad relacionado.

### Smoke

```text
56 passed, 426 deselected in 5.94s
```

## Alcance deliberadamente excluido

D1 no mueve:

- `init_db()`;
- seed metodológico;
- defaults históricos;
- modelos;
- engine;
- SessionLocal;
- Alembic;
- `refresh_progress`.

## Siguiente corte

D2 deberá extraer seed/defaults de manera mecánica y verificable, manteniendo orden de bootstrap e idempotencia. Solo después D3 debe intervenir `init_db()`.

## Condición de materialización

La misma que B1: checkout/patch seguro o blob completo con SHA verificado antes de mover la referencia del branch. No se sustituirá `database.py` con contenido potencialmente truncado.
