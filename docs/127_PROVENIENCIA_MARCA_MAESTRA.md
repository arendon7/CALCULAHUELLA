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

Frontend Kit v1 y front consolidado:

```text
calcula_tu_huella_front_consolidado_v0_37.zip
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

## Auditoría física de entregas disponibles

Se inspeccionaron por nombre de entrada y contenido los paquetes locales disponibles:

```text
calcula_tu_huella_v0_45_1_completa_mac.zip
calcula_tu_huella_v0_45_2_completa_mac.zip
calcula_tu_huella_v0_45_3_completa_mac.zip
calcula_tu_huella_v0_45_4_completa_mac.zip
calcula_tu_huella_v0_45_5_completa_mac.zip
calcula_tu_huella_v0_45_completa_mac(1).zip
calcula-tu-huella-v0-45-5-recuperada.zip
cth_migration_source.zip
CALCULAHUELLA_CARGA_WEB_5_LOTES.zip
CALCULAHUELLA_MIGRACION_CANONICA.zip
CALCULAHUELLA_MIGRACION_CANONICA_V2.zip
CALCULAHUELLA_SUBIDA_DIRECTA_GITHUB.zip
```

Resultado:

- ninguno contiene `logo-oficial.png`, `logo-oficial-blanco.png`, `favicon-64.png` o `favicon-256.png`;
- ninguno contiene el flujo base64 del PNG de 470 × 195 px;
- V0.45.2–V0.45.5 y los paquetes de migración contienen únicamente los SVG legacy `brand-*`;
- los cuatro PNG de `docs/visual/` muestran la identidad anterior y solo pueden utilizarse como referencias históricas de UX;
- la declaración de V0.45.2 sobre “recursos SVG canónicos” no prevalece sobre la decisión posterior de Marca Maestra ni sobre la inspección física de los activos.

Esta reconciliación impide que una etiqueta histórica equivocada vuelva a promover la huella/gráfica como logo oficial.

## Activos descartados como canon

Los siguientes SVG pertenecen a la identidad anterior de huella y gráfica; permanecen temporalmente por compatibilidad, pero no pueden declararse Marca Maestra:

```text
brand-primary.svg
brand-reversed.svg
brand-symbol.svg
logo.svg
logo-white.svg
favicon.svg
```

`brand-primary.svg` contiene además el descriptor antiguo “Plataforma profesional de huella de carbono”. Las láminas v0.45 que muestran esa misma geometría tampoco autorizan su reutilización como logo final.

Los tableros siguientes son **referencias archivísticas de experiencia**, no fuentes de logo:

```text
docs/visual/01_identidad_visual.png
docs/visual/02_landing_dashboard.png
docs/visual/03_inventario.png
docs/visual/04_calculo_reportes.png
```

Sus principios de jerarquía, diagramación y recorridos pueden orientar el producto; está prohibido recortar, extraer o reutilizar su marca anterior.

## Política de recuperación

1. Priorizar los bytes del paquete maestro, `calcula_tu_huella_front_consolidado_v0_37.zip` o el Frontend Kit histórico.
2. Recuperar el logo principal desde HTML autocontenido únicamente si existen dos o más archivos completos, distintos e idénticos en SHA-256.
3. No considerar dos apariciones dentro de un mismo HTML como dos fuentes independientes.
4. Registrar SHA-256, bytes, dimensiones, profundidad, tipo de color y archivos fuente.
5. Comparar las copias disponibles y rechazar cualquier divergencia.
6. No redimensionar, recortar, recolorear, vectorizar ni optimizar el PNG recuperado.
7. No derivar la variante blanca ni los favicons a partir del logo principal.
8. Mantener los SVG actuales como compatibilidad legacy hasta sustituir cada referencia por un binario oficial.
9. No declarar cerrada la v0.45.6 mientras falte alguno de los cuatro activos exactos.

## Herramientas verificables

### Auditoría histórica

`scripts/brand/audit_historical_sources.py` inspecciona archivos, carpetas y ZIP sin modificarlos. Clasifica:

- paquete maestro exacto;
- HTML con PNG principal recuperable;
- activos legacy;
- tableros de referencia visual.

También comprueba si un mismo SHA-256 del PNG 470 × 195 aparece en dos fuentes independientes y puede exigir un paquete completo con `--require-exact-package`.

Ejemplo:

```bash
python3 scripts/brand/audit_historical_sources.py ~/Downloads/*.zip \
  --output instance/brand-history-audit.json
```

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
