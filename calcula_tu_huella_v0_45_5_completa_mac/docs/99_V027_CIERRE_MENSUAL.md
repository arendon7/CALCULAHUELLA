# V0.27 · Conciliación y cierre mensual

## Problema resuelto

V0.26 validaba lotes antes de aplicarlos, pero el inventario seguía abierto durante todo el año. V0.27 introduce una unidad de control mensual para saber exactamente qué fuentes están conciliadas, cuáles conservan advertencias y cuáles impiden el cierre.

## Flujo

1. Seleccionar periodo.
2. Revisar matriz por fuente.
3. Corregir datos, evidencias, hallazgos, factores o cálculos.
4. Enviar el periodo a revisión.
5. Cerrar cuando todas las puertas estén aprobadas.
6. Conservar instantánea y hash SHA-256.
7. Reabrir únicamente mediante excepción auditada.

## Reglas relevantes

- Las fuentes mensuales se esperan todos los meses.
- Las trimestrales se controlan en marzo, junio, septiembre y diciembre.
- Las anuales se controlan en diciembre.
- Las fuentes materiales sin evidencia bloquean.
- Los errores de calidad bloquean.
- Los factores no aprobados y datos sin cálculo bloquean el cierre de emisiones.
- Los datos estimados y calidad C/D generan advertencias.
- Un lote no puede modificar un periodo cerrado.

## Integridad

La instantánea incluye versión del motor, inventario, periodo, métricas y estado de cada fuente. El contenido se serializa de forma canónica y se firma mediante SHA-256. La reapertura conserva el hash anterior.
