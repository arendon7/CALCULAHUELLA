# V1.7 · Support HTTP

## Baseline

`app/support_workflow.py` ya es la autoridad de SLA, asignación por categoría, referencia pública, conversación, visibilidad de mensajes, estados y resumen operativo.

## Corte

Las seis rutas de soporte pasan de `app/main.py` a `app/support_web.py`:

- centro de soporte;
- detalle de caso;
- creación;
- conversación;
- actualización de gestión;
- API resumen.

## Regla crítica

El corte mueve HTTP, no reglas de soporte. No se duplican `response_deadline`, `route_assignment`, `add_support_message`, `support_summary` ni controles de visibilidad cliente/equipo.

## Gates

- `tests/test_v050_support_and_factor_governance.py` protege SLA, referencia, asignación, notas internas, conversación y estado.
- `tests/test_v170_support_routing.py` protege autoridad HTTP, unicidad y disponibilidad del centro/API.
- suite completa, arquitectura y smoke deben quedar verdes antes del commit.
