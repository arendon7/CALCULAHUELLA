# V1.6 · Workflow routing

## Estado previo

La lógica de workflow ya estaba separada en `workflow_domain.py`, `workflow_service.py`, `workflow_bridge.py` y `workflow_integrations.py`. La deuda restante era HTTP: las cinco rutas de `Mi trabajo` y su inyección de navegación convivían con `/guia` dentro de `experience_web.py`.

## Corte materializado

- `app/workflow_web.py` pasa a ser la autoridad HTTP de las 5 rutas `/mi-trabajo*`.
- La promoción de `Mi trabajo` en la navegación se mueve con esa superficie.
- `app/experience_web.py` queda dedicado a `/guia`, `GUIDE_STAGES` y `GLOSSARY`.
- `app/main.py` solo registra ambos módulos.
- No se modifican estados, transiciones, capacidades, sincronización de `DataRequest`, notificaciones ni reglas de asignación.

## Contratos

1. Exactamente cinco rutas de workflow, sin duplicados.
2. `/mi-trabajo`, `/api/mi-trabajo` y `/guia` permanecen operativos.
3. Iteration 15 protege el catálogo canónico.
4. Iteration 16 protege asignación, visibilidad y ciclo completo.
5. Iteration 17 protege integración y sincronización.
6. Suite completa, arquitectura y smoke deben quedar verdes antes del commit.
