# V1.7 · Customer Success HTTP

## Autoridad

`app/customer_success_web.py` pasa a ser la autoridad HTTP de ocho contratos de éxito del cliente: vista de cuenta, perfil, recálculo de salud, hitos, compromisos y estrategia de renovación.

## Dominio preservado

`app/customer_success.py` continúa siendo la autoridad de `account_metrics`, `refresh_account_health` y `sync_renewal_opportunity`. El refactor no modifica ponderaciones, puntajes, reglas de riesgo ni probabilidad de renovación.

## Acceso y aislamiento

La vista sigue disponible para roles con `view_customer_success` o `manage_customer_success`; las mutaciones exigen `manage_customer_success`. Hitos, compromisos, inventarios y renovaciones siguen restringidos a la organización activa.

## Gates

Los contratos históricos V0.17 protegen datos semilla, lectura del cliente, actualización de perfil/salud, ciclo de hitos, ciclo de compromisos y estrategia de renovación. El contrato V1.7 protege autoridad HTTP, unicidad y permisos de lectura/escritura.
