# V1.6 · D2 seed/defaults

## Objetivo

Reducir la concentración de `app/database.py` sin modificar modelos ORM, migraciones, cálculos ni datos funcionales.

## D2a · bootstrap de semilla

- `app/seed.py` pasa a ser la autoridad del bootstrap y de la carga demostrativa ejecutada por `init_db()`.
- `app.database.init_db()` permanece como fachada pública compatible.
- Los modelos continúan en `app/db/models`; `Base`, `ENGINE`, `SessionLocal` y rutas de almacenamiento continúan en `app/db/base`.
- Los defaults históricos permanecen temporalmente en `app/database.py`; su extracción corresponde a D2b y no se mezcla con este corte.
- No se modifican factores, GWP, fórmulas, emisiones, tablas ORM ni migraciones.

## Contratos de aceptación

1. La inicialización completa de la suite sigue creando la misma semilla demostrativa.
2. Ejecutar `init_db()` sobre una base ya sembrada no duplica organizaciones.
3. El esquema conserva 124 tablas.
4. `database.py` reduce materialmente su tamaño y deja de contener el dataset principal de `Industrias Andinas Demo`.
5. Regresión completa, deuda arquitectónica, smoke y Alembic deben quedar verdes antes del commit.

## Siguiente corte

D2b extraerá la cadena `_ensure_v012_defaults` → `_ensure_v100_final_defaults` a una autoridad específica de defaults, conservando fachadas privadas solo si existe dependencia real comprobada.
