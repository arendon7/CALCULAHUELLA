# V1.9 · Automations HTTP

## Autoridad

`app/automations_web.py` pasa a ser la autoridad HTTP de cinco contratos: panel, creación, activación/desactivación, ejecución manual y procesamiento de automatizaciones vencidas.

## Dominio preservado

`app/automations.py` conserva tipos, cadencias, cálculo de próxima ejecución, ejecución individual y procesamiento del scheduler. No se cambian reglas de tiempo, roles destinatarios, auditoría o semántica de `AutomationRun`.

## Acceso

Todas las rutas continúan exigiendo `manage_automations`. Las automatizaciones y sus ejecuciones permanecen aisladas por organización; el inventario opcional se valida mediante `get_inventory`.

## Gates

El contrato histórico `test_manual_automation_execution_creates_run` protege ejecución real y cierre de `AutomationRun`. El contrato V1.9 protege autoridad HTTP, unicidad, permisos y creación persistente con `next_run_at`.
