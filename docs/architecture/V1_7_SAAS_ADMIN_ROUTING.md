# V1.7 · SaaS Administration HTTP

## Autoridad

`app/saas_admin_web.py` pasa a ser la autoridad HTTP de cuatro contratos administrativos: panel SaaS, creación de plan, actualización de suscripción y actualización del estado de cobro.

## Alcance

El corte no mueve `/cuenta-servicio`, onboarding, diagnóstico comercial ni pagos. Tampoco cambia límites de planes, estados de suscripción, ciclos de cobro o semántica de `BillingInvoice`.

## Permisos

Las cuatro rutas continúan exigiendo `manage_saas`. La actualización de suscripción conserva plan, estado, ciclo, tarifa personalizada, renovación y notas; la actualización de cobro conserva la marca temporal de pago.

## Gates

El test histórico `test_saas_admin_can_create_plan` protege creación de planes. El contrato V1.7 protege autoridad HTTP, unicidad, denegación para cliente y persistencia de actualización de suscripción/cobro.
