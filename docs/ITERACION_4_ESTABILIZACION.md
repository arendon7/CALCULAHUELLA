# Iteración 4 · estabilización integral

## Objetivo

Validar el flujo transversal antes de añadir nuevas capacidades. Esta iteración
corrige regresiones de sincronización, reduce notificaciones redundantes y crea
una compuerta de CI reproducible para migraciones, aislamiento y suite completa.

## Correcciones de dominio

Los módulos especializados utilizan estados más simples que `WorkItem`. La
sincronización anterior podía mover una tarea hacia atrás, por ejemplo:

- Aceptada por revisor → En revisión.
- Cerrada → Aceptada por revisor.
- Aceptada por revisor → En implementación.

La política nueva conserva el estado canónico más avanzado. Los registros de
origen siguen siendo autoritativos cuando expresan una devolución, bloqueo,
cancelación, cierre o reapertura.

## Notificaciones

- El actor de una transición no recibe una notificación sobre su propia acción.
- Una asignación directa no se convierte después en un aviso masivo por rol.
- Los avisos por rol excluyen al usuario que ejecutó la transición.
- Se mantiene una sola notificación por destinatario y transición.

## Validación ejecutada

- Sintaxis Python de la capa, instalación y pruebas: aprobada.
- Sintaxis YAML del workflow: aprobada.
- Política de precedencia: seis casos críticos aprobados.
- Prueba aislada del adaptador: seis grupos aprobados.
- Instalación idempotente: aprobada.
- Exclusión del actor y deduplicación por usuario: aprobadas.

## Validación de CI preparada

El workflow de estabilización se activa por `push`, `pull_request` y ejecución
manual, y contempla:

1. Compilación Python.
2. Verificación canónica.
3. Pruebas dirigidas de Iteraciones 1–4.
4. Alembic desde base vacía.
5. Alembic desde `20260805_0036` hasta head.
6. Suite smoke.
7. Suite integral en procesos aislados.
8. Publicación de evidencia como artefacto.

## Limitación de ejecución

Los commits realizados por el conector no generaron ejecuciones de GitHub
Actions. La compuerta está preparada, pero las migraciones y suites del árbol
completo no se presentan como aprobadas hasta que exista una ejecución real.

## Compuertas

El PR continúa en borrador hasta que CI termine correctamente y se revisen los
resultados de navegador y dispositivos físicos.
