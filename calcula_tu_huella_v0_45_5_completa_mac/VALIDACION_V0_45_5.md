# Validación V0.45.5 — importación y corrección guiada

## Alcance validado

- Lectura de CSV y XLSX.
- Selección de hoja, fila de encabezados y separador.
- Detección y mapeo de columnas.
- Validación previa sin modificar el inventario.
- Corrección y revalidación individual de filas.
- Aplicación controlada y políticas de duplicados.
- Seguridad, permisos, entorno demo y certificación.
- Compatibilidad con onboarding, marca y primer inventario.
- Scripts de instalación y ciclo de vida macOS.

## Resultados

- 73 pruebas focalizadas aprobadas.
- 64 plantillas Jinja compiladas.
- Python compilado sin errores.
- JavaScript validado con `node --check`.
- Scripts `.sh` y `.command` validados con `bash -n`.
- API de salud alineada en versión 0.45.5.
- Aplicación macOS, instalador y manifiesto de marca alineados en 0.45.5.

## Pruebas nuevas de V0.45.5

- Excel con encabezados fuera de la primera fila.
- Relectura desde navegador con fila de encabezados personalizada.
- Corrección de una fila inválida sin recargar el archivo.
- Revalidación y actualización automática del estado del lote.
- Editor de filas y control visual del mapeo mínimo.

## Limitación de ejecución

La batería histórica completa no se ejecutó como un único proceso porque la reinicialización repetida de la base demo supera el límite operativo del entorno. Los dominios afectados y las regresiones críticas se ejecutaron por grupos e individualmente.

## Invariantes

No se modificaron factores de emisión, fórmulas, conversiones, reglas metodológicas, modelos de base de datos ni migraciones.
