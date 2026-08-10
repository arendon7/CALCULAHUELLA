# V1.9 · Platform Administration HTTP

## Autoridad

`app/platform_admin_web.py` pasa a ser la autoridad HTTP de cuatro contratos: panel de operación avanzada, configuración por organización, notificación de prueba y procesamiento de la cola.

## Semántica preservada

Se mantienen `PlatformSetting`, normalización de claves, auditoría, `notify_roles`, `process_pending_notifications`, tamaño de lote y diagnóstico de almacenamiento. Las preferencias personales `/notificaciones*` permanecen fuera de este corte.

## Acceso

Las cuatro rutas continúan exigiendo `manage_operations` y filtrando configuración/estadísticas por organización activa.

## Gates

V0.11 protege configuración persistente, notificación de prueba, procesamiento de cola y denegación a no administradores. El contrato V1.9 protege autoridad HTTP y unicidad.
