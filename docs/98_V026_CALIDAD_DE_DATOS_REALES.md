# V0.26 · Calidad y aplicación controlada de datos reales

## Problema resuelto

La V0.25 podía importar datos al piloto, pero la carga y la aplicación estaban demasiado próximas. V0.26 introduce un preflight persistente: cada archivo se registra como lote, se valida por fila y solo después de superar los controles puede modificar el inventario.

## Modelo operativo

`Plantilla → validación → hallazgos → corrección → aplicación → recálculo → auditoría`

## Reglas

- DQ-001–003: identidad y periodo.
- DQ-004–006: valor y justificación de ceros.
- DQ-007–009: unidad y conversión dimensional.
- DQ-010–011: duplicidad y actualización de periodos.
- DQ-012–013: evidencia y estimaciones.
- DQ-014: valores atípicos.

## Integridad

El hash SHA-256 evita volver a cargar exactamente el mismo archivo. La validación no crea `ActivityData`. La aplicación es una acción separada y auditada.

## Pendiente para el piloto

La plataforma está preparada para recibir datos reales, pero Greenatics debe suministrar o confirmar los archivos fuente, responsables, periodos y evidencia. Los factores pendientes continúan bloqueando el cierre formal.
