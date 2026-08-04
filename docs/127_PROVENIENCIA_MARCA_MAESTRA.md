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

La guía de integración identifica `static/img/brand/` como la ubicación de los activos oficiales exactos. El demo interno utiliza expresamente `logo-oficial-blanco.png` sobre la barra lateral oscura; el sitio público utiliza `logo-oficial.png` en navegación y footer, además de los dos favicons.

## Copias autocontenidas recuperadas

Tres artefactos históricos conservan el logo principal como un PNG embebido mediante `data:image/png;base64`:

```text
v0_44_experiencia.html
experiencia_interna.html
index.html autocontenido de Marca Maestra v1
```

Las copias identificadas declaran un PNG de **470 × 195 px** y muestran la misma secuencia de bytes en los fragmentos cotejados. La recuperación definitiva debe decodificar cada archivo completo, comprobar el cierre `IEND` y exigir un único SHA-256 común presente en al menos dos archivos históricos independientes.

## Activos descartados como canon

Los siguientes SVG pertenecen a la identidad anterior de huella y gráfica; permanecen temporalmente por compatibilidad, pero no pueden declararse Marca Maestra:

```text
brand-primary.svg
brand-reversed.svg
brand-symbol.svg
```

`brand-primary.svg` contiene además el descriptor antiguo “Plataforma profesional de huella de carbono”. Las láminas v0.45 que muestran esa misma geometría tampoco autorizan su reutilización como logo final.

## Política de recuperación

1. Priorizar los bytes del paquete maestro o del Frontend Kit histórico.
2. Recuperar el logo principal desde HTML autocontenido únicamente si existen dos o más archivos completos, distintos e idénticos en SHA-256.
3. No considerar dos apariciones dentro de un mismo HTML como dos fuentes independientes.
4. Registrar SHA-256, bytes, dimensiones, profundidad, tipo de color y archivos fuente.
5. Comparar las copias disponibles y rechazar cualquier divergencia.
6. No redimensionar, recortar, recolorear, vectorizar ni optimizar el PNG recuperado.
7. No derivar la variante blanca ni los favicons a partir del logo principal.
8. Mantener los SVG actuales como compatibilidad legacy hasta sustituir cada referencia por un binario oficial.
9. No declarar cerrada la v0.45.6 mientras falte alguno de los cuatro activos exactos.

## Herramientas verificables

### Paquete completo

`scripts/brand/import_master_package.py` recibe el ZIP o la carpeta histórica, localiza los cuatro archivos exactos, valida PNG, transparencia y tamaños de favicon, calcula sus huellas y solo después permite instalarlos con `--apply`.

### HTML autocontenido

`scripts/brand/extract_embedded_master.py` recibe dos o más HTML históricos independientes, localiza las imágenes PNG con texto alternativo “Calcula tu Huella”, valida firma, `IHDR`, cierre `IEND`, dimensiones de 470 × 195 y coincidencia SHA-256. Al usar `--apply` escribe exclusivamente:

```text
app/static/img/brand/logo-oficial.png
app/static/img/brand/logo-oficial.provenance.json
```

No modifica plantillas ni genera los otros tres activos.

Comando normalizado:

```bash
make brand-recover-primary BRAND_HTML_SOURCES="v0_44_experiencia.html experiencia_interna.html"
```

La instalación completa continúa exigiendo:

```bash
make brand-require-master
```
