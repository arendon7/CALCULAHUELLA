# Iteración 3 · Orquestación transversal de trabajo

## Objetivo

Incorporar en `Mi trabajo` los registros que todavía vivían de forma aislada
en revisión, calidad, cierre mensual, informes, reducción y soporte.

## Registros conectados

- `DataRequest`
- `ReviewObservation`
- `DataQualityFinding`
- `PeriodClose`
- `ReportArtifact`
- `ReductionAction`
- `SupportTicket`

Cada registro especializado conserva su autoridad. `WorkItem` actúa como
índice operativo transversal, no como sustituto prematuro.

## Sincronización

La sincronización es idempotente:

1. Localiza el registro de origen.
2. Busca una tarea por organización, tipo de entidad e identificador.
3. Crea o actualiza la tarea.
4. Conserva el enlace al módulo original.
5. No crea una segunda tarea al abrir nuevamente la bandeja.
6. Si el módulo original cambió, refleja el nuevo estado en `Mi trabajo`.

## Sincronización bidireccional

Las transiciones ejecutadas desde `Mi trabajo` actualizan el registro original:

- Las observaciones reciben respuesta, resolución y cierre.
- Los hallazgos de calidad se marcan en revisión, resueltos o ignorados.
- Los cierres mensuales pasan a revisión, cierre o reapertura.
- Los informes pasan a revisión, devolución o aprobación.
- Las acciones de reducción reflejan implementación, seguimiento, pausa o descarte.
- Los tickets de soporte conservan estado, resolución y mensajes.

## Conversación contextual

Los comentarios ingresados al ejecutar una transición:

- se guardan en `WorkItemEvent`;
- permanecen vinculados con la tarea;
- en tickets de soporte se replican como `SupportMessage`;
- acompañan devoluciones, bloqueos, reaperturas y decisiones.

El módulo especializado sigue disponible mediante “Abrir el registro de origen”.

## Notificaciones

Se generan notificaciones para:

- nueva asignación;
- devolución o bloqueo;
- entrega para validación;
- envío a revisión;
- aceptación;
- cierre;
- reapertura.

La notificación dirige al elemento exacto dentro de `/mi-trabajo`.

## Compatibilidad

- No cambia la landing pública.
- No modifica el logo clásico.
- No elimina ninguna tabla o ruta anterior.
- No fusiona el PR.
- Mantiene la respuesta pública de `sync_data_requests` con las claves
  `total` y `changed` para evitar regresiones.

## Compuertas pendientes

- Ejecución real de GitHub Actions.
- Migración Alembic completa en una base nueva y una base actualizada.
- Pruebas de aislamiento multiempresa.
- Pruebas en navegador real de la bandeja con todas las categorías.
- Revisión de duplicidad entre notificaciones de módulos y notificaciones de flujo.
