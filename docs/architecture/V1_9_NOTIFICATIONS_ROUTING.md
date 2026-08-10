# V1.9 · Notifications HTTP

## Autoridad

`app/notifications_web.py` pasa a ser la autoridad HTTP de cuatro contratos personales: bandeja, lectura individual, lectura masiva y preferencias.

## Semántica preservada

Se mantienen `read_at`, enlace de retorno, preferencias `email_enabled` / `in_app_enabled` y frecuencias `Inmediato`, `Diario` y `Semanal`.

## Aislamiento

La bandeja y las mutaciones conservan el filtro simultáneo por `organization_id` y `user_id`; una notificación no puede operarse desde otro usuario u organización mediante estas rutas.

## Gates

V0.11 protege lectura individual y persistencia de preferencias. El contrato V1.9 protege autoridad HTTP, unicidad y presencia explícita de ambos filtros de aislamiento.
