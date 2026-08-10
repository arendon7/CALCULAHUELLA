# V1.8 · Climate Risk HTTP

## Autoridad

`app/climate_risk_web.py` pasa a ser la autoridad HTTP de nueve contratos: evaluación climática, registro/actualización de riesgos, controles, hoja de ruta, acciones y exportación XLSX.

## Dominio preservado

`app/climate_risk.py` continúa siendo la autoridad de `assessment_summary`, `calculate_risk_scores`, `risk_level`, `synchronize_control_effectiveness` y `refresh_assessment_status`. No se alteran escalas 1–5, cálculo inherente/residual, efectividad combinada, exposición financiera ni readiness.

## Acceso e aislamiento

La lectura continúa disponible para `view_climate_risk` o `manage_climate_risk`; las mutaciones exigen `manage_climate_risk`. Riesgos, controles, acciones e inventarios siguen restringidos a la organización activa.

## Gates

Los contratos históricos V0.19 protegen semilla, lectura cliente, scoring inherente/residual, efecto de controles, ciclo de acciones y exportación Excel. El contrato V1.8 protege autoridad HTTP, unicidad y permisos.
