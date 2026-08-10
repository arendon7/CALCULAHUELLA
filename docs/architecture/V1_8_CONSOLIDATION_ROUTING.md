# V1.8 · Consolidation / Release Governance HTTP

## Autoridad

`app/consolidation_web.py` pasa a ser la autoridad HTTP de siete contratos: panel de consolidación, hallazgos, puertas de release, recorridos por rol, exportación XLSX y APIs de arquitectura/consolidación.

## Dominio preservado

`app/consolidation.py` conserva la autoridad de `consolidation_summary`, `build_consolidation_workbook` y `summary_json`; `app/architecture.py` conserva `domain_architecture_summary`. No se alteran criterios de readiness, evidencia de pruebas, estados de hallazgos, gates o recorridos.

## Acceso

La lectura continúa exigiendo `view_consolidation`; las mutaciones exigen `manage_consolidation`. Cliente permanece sin acceso y Verificador mantiene lectura sin mutación.

## Gates

`tests/test_v021_consolidation.py` protege defaults, readiness controlado, permisos, mutaciones de hallazgos/gates/recorridos, XLSX y registro de producto. El contrato V1.8 protege autoridad y unicidad HTTP.
