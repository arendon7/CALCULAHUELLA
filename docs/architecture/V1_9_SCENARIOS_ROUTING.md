# V1.9 · Scenarios HTTP

## Autoridad

`app/scenarios_web.py` pasa a ser la autoridad HTTP de tres contratos: panel, creación y configuración de escenarios de reducción.

## Dominio preservado

`app/scenarios.py` conserva `get_scenario`, `scenario_summary` y `portfolio_macc`. No se alteran baseline, reducción total, inversión, ahorro, NPV, payback, MACC, adopción o cronograma.

## Límites

Verification no forma parte de este corte. Las mutaciones continúan exigiendo `manage_inventory` y un inventario editable; la lectura sigue disponible al usuario autenticado dentro de su organización.

## Gates

Los contratos históricos V0.8 protegen resumen financiero semilla y creación/configuración persistente. El contrato V1.9 protege autoridad HTTP, unicidad y lectura sin mutación para Cliente.
