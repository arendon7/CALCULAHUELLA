# Calcula tu Huella V0.45.5 · importación y corrección guiada

Esta revisión convierte la carga masiva en un flujo completo: lectura configurable de CSV/XLSX, previsualización, mapeo de columnas, validación por fila, corrección dentro de la plataforma y aplicación controlada al inventario.

No modifica factores de emisión, conversiones, fórmulas, metodología, modelos de datos ni migraciones.

## Cambios principales

- Selección de hoja en archivos Excel.
- Configuración de la fila real de encabezados.
- Detección o selección del separador CSV.
- Mapeo automático y manual de columnas.
- Indicador de campos mínimos antes de validar.
- Política controlada para duplicados: rechazar, omitir o actualizar.
- Corrección individual de fuente, fechas, valor, unidad, origen, evidencia y condición estimada.
- Revalidación inmediata sin volver a cargar el archivo.
- Cierre trazable de hallazgos anteriores.
- Historial separado por inventario activo.

## Recorrido recomendado

1. Crea o selecciona el inventario.
2. Confirma sus fuentes de emisión.
3. Entra a **Cargas operativas**.
4. Carga un archivo CSV o XLSX.
5. Ajusta hoja, encabezados o separador cuando sea necesario.
6. Relaciona las columnas y valida el lote.
7. Corrige las filas señaladas dentro de la plataforma.
8. Aplica el lote cuando no queden errores.

## Inicio en macOS

1. Descomprime completamente el ZIP.
2. Abre `INSTALAR_O_ACTUALIZAR_CALCULA_TU_HUELLA.command`.
3. Luego abre `ABRIR_CALCULA_TU_HUELLA.command`.
4. Ingresa con un usuario demo.

La actualización conserva base de datos, evidencias, informes, importaciones, respaldos y certificados en `~/Library/Application Support/CalculaTuHuella`.

## Acceso demo

Contraseña común: `Demo2026!`

- `admin@calculatuhuella.local`
- `consultor@calculatuhuella.local`
- `cliente@calculatuhuella.local`
- `revisor@calculatuhuella.local`
- `verificador@calculatuhuella.local`

## Certificación

- `14_CERTIFICAR_VERSION.command`: validación local o productiva.
- `15_PREPARAR_Y_CERTIFICAR_DEMO.command`: preparación y verificación del entorno demostrativo.

La certificación productiva estricta continúa condicionada a servicios externos reales.
