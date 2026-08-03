# V0.25 · Beta guiada y ejecución controlada del piloto Greenatics

## Propósito

Pasar de una matriz de preparación a un flujo operativo que permita recopilar datos reales, calcular, documentar incidencias, contrastar resultados y decidir si el piloto está listo para aprobación.

## Flujo implementado

1. Iniciar la ejecución desde la matriz Greenatics.
2. Crear un inventario 2026 y vincular Yarumal, Támesis y la operación corporativa.
3. Crear fuentes y solicitudes para cada requisito incluido.
4. Asignar automáticamente únicamente factores aprobados y compatibles.
5. Descargar una plantilla Excel con doce periodos por fuente mensual.
6. Importar datos, actualizar solicitudes, recalcular emisiones y avance.
7. Registrar incidencias metodológicas, operativas y de límites.
8. Comparar el total de la plataforma con una memoria independiente.
9. Aplicar un umbral piloto de variación máxima del 2 %.
10. Bloquear la aprobación mientras existan datos, factores, incidencias o contraste pendientes.

## Controles de integridad

- Inicio idempotente: repetir la acción no crea un segundo piloto.
- Códigos de fuente limitados a la ejecución activa.
- Validación de fechas, valores, unidades y año del inventario.
- Actualización por fuente y periodo sin duplicar registros.
- Conservación de la auditoría y del usuario que ejecuta cada acción.
- Separación entre total calculado por la plataforma y total independiente.

## Límites

La conformidad del contraste es una puerta interna del piloto. No equivale a una verificación externa ni convierte en formales los factores todavía clasificados como demostrativos, piloto o pendientes de aprobación.
