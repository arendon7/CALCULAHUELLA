# V1.9 · Service Account HTTP

## Autoridad

`app/service_account_web.py` pasa a ser la autoridad HTTP de dos contratos: cuenta de servicio y actualización administrativa de suscripción. `_service_usage` se mueve con el contexto porque solo alimenta esta superficie.

## Semántica preservada

Se mantienen límites de usuarios, sedes, inventarios y almacenamiento; persistencia mensual de `UsageCounter`; planes activos; ciclo mensual/anual; y la aclaración de que el cambio de plan es administrativo y no procesa pagos.

## Acceso

La cuenta continúa visible al usuario autenticado. La actualización de suscripción exige `manage_subscription` y se limita a la organización activa.

## Gates

El contrato histórico `test_service_account_has_seeded_subscription_and_plans` protege la lectura semilla. El contrato V1.9 protege autoridad HTTP, unicidad, lectura de cliente y persistencia del cambio de plan.
