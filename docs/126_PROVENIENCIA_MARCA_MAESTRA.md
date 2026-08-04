# Proveniencia de la Marca Maestra v1

## Decisión aprobada

El 3 de agosto de 2026 se consolidó una única identidad para **Calcula tu Huella**. La composición aprobada utiliza una C circular envolvente, barras ascendentes, una hoja integrada y el nombre exacto “Calcula tu Huella”.

No se permiten redibujos, aproximaciones, deformaciones ni sustituciones.

## Artefactos históricos identificados

```text
calcula_tu_huella_marca_maestra_v1.zip
calcula_tu_huella_marca_maestra_v1/
  board_maestro_identidad_calcula_tu_huella_v1.png
```

Frontend Kit v1:

```text
static/img/brand/
  logo-oficial.png
  logo-oficial-blanco.png
  favicon-64.png
  favicon-256.png
```

La guía de integración del Frontend Kit identifica `static/img/brand/` como la ubicación de los activos oficiales exactos. Las demos históricas referencian directamente esos nombres y las versiones autocontenidas conservan el logo como PNG embebido.

## Política de recuperación

1. Priorizar los bytes del paquete maestro o del Frontend Kit histórico.
2. Aceptar el PNG embebido únicamente cuando su flujo de bytes pueda recuperarse completo y verificarse.
3. Registrar SHA-256, bytes, dimensiones, profundidad y transparencia.
4. Comparar las copias disponibles y rechazar cualquier divergencia.
5. No derivar la variante blanca ni los favicons a partir de una descripción.
6. No declarar cerrada la v0.45.6 mientras falte alguno de los cuatro activos exactos.

## Importador verificable

`scripts/brand/import_master_package.py` recibe el ZIP o la carpeta histórica, localiza los cuatro archivos exactos, valida PNG, transparencia y tamaños de favicon, calcula sus huellas y solo después permite instalarlos con `--apply`.

El importador no transforma las imágenes.
