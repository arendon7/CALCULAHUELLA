# V1.9 · Dashboard and core workspace HTTP

## Autoridad

`app/dashboard_web.py` pasa a ser la autoridad HTTP de tres contratos de experiencia núcleo: preferencia de vista, recorrido del inventario y dashboard.

## Semántica preservada

La preferencia conserva normalización `essential/full`, flash y protección de `return_url`. El recorrido conserva `guided_workspace` + `journey_detail`. El dashboard mantiene métricas, solicitudes activas, siguiente acción por rol, readiness de entrega, onboarding, perfil guiado y relato demo.

## Frontera

`_parse_excel_period` y los helpers transversales permanecen fuera. `/modulos`, `/api/health` y `/api/ready` continúan en `main.py` como endpoints propios del composition root/sistema.

## Gates

`test_core_pages_load` protege disponibilidad histórica de dashboard y recorrido. Los contratos V1.9 protegen autoridad HTTP, unicidad, acceso de Cliente y la barrera contra retorno externo.
