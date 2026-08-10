# V1.6 · Methodology / Calculation Boundary · Calculation HTTP

## Corte

- `GET /calculos` y `POST /inventarios/{inventory_id}/recalcular` pasan a `app/calculation_web.py`.
- `app/main.py` conserva únicamente el registro del módulo.
- `app/calculations.py` sigue siendo la autoridad de `recalculate_inventory` y `source_calculation_summary`.

## Regla crítica

Este corte mueve **orquestación HTTP**, no cálculo. No se copian ni modifican fórmulas, conversiones, factores, gases, GWP, snapshots ni reglas de error/alerta.

## Contratos

1. Exactamente dos rutas, sin duplicados.
2. `/calculos` sigue operativo.
3. Recalcular mantiene redirect y usa el motor existente.
4. La estructura de resultados por fuente permanece compatible.
5. Suite completa, arquitectura y smoke verdes antes del commit.
