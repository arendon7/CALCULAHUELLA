# V1.8 · Impact Intelligence HTTP

## Autoridad

`app/impact_intelligence_web.py` pasa a ser la autoridad HTTP de cinco contratos: panel de impacto, recálculo de snapshot, alta de benchmark, cambio de estado de benchmark y exportación XLSX.

## Dominio preservado

`app/impact_intelligence.py` continúa siendo la autoridad de `impact_metrics`, `refresh_impact_snapshot`, `compare_benchmarks` y `portfolio_comparison`. No se alteran puntajes, intensidades, cobertura de evidencia, ahorro, reducción esperada ni reglas de comparación.

## Acceso

La lectura continúa disponible para `view_impact` o `manage_impact`; las mutaciones exigen `manage_impact`. Benchmarks y snapshots siguen limitados a la organización activa.

## Gates

Los contratos históricos V0.18 protegen semilla, lectura cliente, recálculo, creación/archivo de benchmark y exportación Excel. El contrato V1.8 protege autoridad HTTP, unicidad y lectura sin permisos de mutación.
