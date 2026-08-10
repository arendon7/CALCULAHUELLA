# V1.9 · Analytics HTTP

## Autoridad

`app/analytics_web.py` pasa a ser la autoridad HTTP de tres contratos: panel de análisis y creación/edición de indicadores operativos.

## Dominio preservado

`app/analytics.py` conserva `full_analysis` y las métricas derivadas. El corte no toca cálculo de emisiones, factores, escenarios ni reducción. `ActivityIndicator` mantiene persistencia y aislamiento por inventario/organización.

## Separación deliberada

Dashboard no forma parte de este corte porque agrega workflow, entrega profesional, onboarding y configuración guiada. `_parse_excel_period` tampoco pertenece a Analytics y permanece en su ubicación actual hasta delimitar su consumidor real.

## Gates

El contrato histórico V0.6 protege persistencia de indicadores e integración con reducción. El contrato V1.9 protege autoridad HTTP, unicidad y lectura sin permisos de mutación.
