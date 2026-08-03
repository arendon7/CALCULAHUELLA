# V0.29 · Cargas operativas configurables

## Objetivo

Conectar archivos operativos reales con el inventario GEI sin exigir una plantilla rígida y sin eliminar los controles existentes de calidad, evidencia, cálculo o cierre mensual.

## Flujo

1. Seleccionar inventario y perfil opcional.
2. Cargar CSV/XLSX y previsualizar encabezados.
3. Mapear columnas y valores predeterminados.
4. Validar el lote completo sin modificar el inventario.
5. Revisar filas, errores, advertencias y duplicados.
6. Aplicar únicamente lotes sin errores.
7. Recalcular las fuentes afectadas y actualizar avance.
8. Consultar auditoría y descargar hallazgos.

## Reglas principales

- OP-001: fuente ausente o no resoluble.
- OP-002 a OP-004: fechas inválidas o fuera del inventario.
- OP-005 a OP-007: valor inválido, negativo o cero sin justificación.
- OP-008 a OP-010: unidad ausente o incompatible y origen no reconocido.
- OP-011: fuente material sin referencia de evidencia.
- OP-012: duplicado dentro del archivo.
- OP-013: dato existente según política seleccionada.
- OP-014: periodo cerrado o no editable.
- OP-015: máximo de filas excedido.
- OP-016: archivo sin datos.

## Modelo de datos

- `operational_import_profiles`: configuración reutilizable.
- Extensiones en `data_import_batches`: inventario, perfil, formato, hoja y mapeo.
- Extensiones en `data_import_rows`: dato original, huella SHA-256 y vínculo al registro duplicado.

## Seguridad

- Archivos admitidos: CSV y XLSX.
- Validación de extensión, MIME y firma básica mediante el control de cargas existente.
- Límite de tamaño configurado por `MAX_UPLOAD_MB`.
- Previsualizaciones temporales con token criptográfico, expiración de 24 horas y asociación a organización.
- Operaciones de validación y aplicación protegidas por permisos y CSRF.
