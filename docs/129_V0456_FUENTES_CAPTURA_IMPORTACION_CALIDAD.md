# V0.45.6 — Fuentes, captura, importación y calidad

## Propósito

Convertir las superficies de información del inventario en un recorrido continuo y comprensible:

```text
Fuentes → Datos → Evidencias → Calidad → Cálculo
```

La intervención es una mejora progresiva de presentación y accesibilidad. No modifica rutas, modelos, permisos, cálculos, migraciones, formatos de archivo ni contratos Jinja.

## Problema identificado

La versión funcional ya permitía:

- configurar fuentes;
- registrar datos manuales;
- asociar evidencias;
- importar Excel;
- mapear CSV/XLSX operativos;
- validar lotes;
- corregir filas;
- gestionar hallazgos;
- aplicar información al inventario;
- recalcular emisiones.

Sin embargo, cada página explicaba su propio proceso y el usuario perdía la relación entre las etapas. Las tablas extensas tampoco ofrecían búsqueda local y los campos de archivo no anunciaban claramente qué documento había sido seleccionado.

## Navegador de flujo

`app/static/js/cth-guided.js` detecta las páginas relacionadas con datos e inserta un navegador de cinco etapas después del encabezado principal.

Rutas cubiertas:

```text
/inventarios/{id}/fuentes
/informacion
/informacion/importar
/cargas-operativas
/calidad-datos
/calculos
/fuentes/{id}
```

Etapas:

1. **Fuentes** — definir el mapa operativo.
2. **Datos** — capturar actividad manual o masivamente.
3. **Evidencias** — respaldar valores y periodos.
4. **Calidad** — resolver validaciones y hallazgos.
5. **Cálculo** — consolidar y revisar CO₂e.

La etapa actual utiliza `aria-current="step"`. En `/informacion`, el hash `#evidencias` actualiza la etapa activa sin recargar la página.

## Selección de archivos

Los campos `input[type="file"]` de las superficies autenticadas se mejoran de forma progresiva:

- muestran el nombre del archivo;
- muestran su tamaño;
- anuncian el cambio mediante `aria-live`;
- conservan el input nativo y su validación;
- advierten visualmente cuando la selección supera 10 MB;
- no bloquean ni reemplazan la validación del servidor.

La mejora se aplica a:

- importación Excel;
- cargas operativas CSV/XLSX;
- centro de calidad;
- carga de evidencias.

## Búsqueda local en tablas

Se añade un buscador no destructivo a la tabla principal de:

- mapa de fuentes;
- registros de actividad;
- historial de cargas operativas;
- historial de lotes de calidad.

La búsqueda:

- no realiza solicitudes al servidor;
- no modifica ni elimina registros;
- ignora mayúsculas y tildes;
- anuncia cuántas filas permanecen visibles;
- muestra un estado vacío cuando no hay coincidencias.

## Tablas responsive

Cada `.responsive-table` se declara como región navegable por teclado:

- `tabindex="0"`;
- `role="region"`;
- nombre accesible tomado del encabezado más cercano;
- foco visible;
- desplazamiento horizontal conservado en móvil.

## Sistema visual

`app/static/css/cth-data-flow.css` incorpora:

- navegación horizontal responsive;
- etapa activa alineada con la paleta oficial;
- buscadores de tabla;
- selección de archivos;
- jerarquía de mapeos requeridos;
- estados de preparación del lote;
- franjas de resumen;
- diferenciación de errores y advertencias;
- editores de fila integrados;
- adaptación para 920 y 620 px.

La hoja se importa desde `cth-tokens.css`, después de las capas de componentes, shell, guías y dashboard.

## Compatibilidad funcional

Las pruebas verifican que continúen presentes los contratos críticos:

```text
/inventarios/{id}/fuentes/nueva
/informacion/datos/nuevo
/informacion/evidencias/nueva
/informacion/plantilla.xlsx
/cargas-operativas/previsualizar
/cargas-operativas/validar
/calidad-datos/cargar
/calidad-datos/lotes/{id}/aplicar
```

La nueva capa no modifica ningún `action`, `method`, `enctype`, nombre de campo o variable Jinja.

## Archivos incorporados o actualizados

```text
app/static/css/cth-data-flow.css
app/static/css/cth-tokens.css
app/static/js/cth-guided.js
tests/test_v0456_data_flow_experience.py
.github/workflows/ci.yml
docs/129_V0456_FUENTES_CAPTURA_IMPORTACION_CALIDAD.md
```

## Criterios de aceptación

- navegador visible en las rutas de datos;
- etapa actual semánticamente identificada;
- archivos seleccionados anunciados;
- búsqueda de tablas funcional sin backend;
- tablas navegables por teclado;
- ninguna ruta o acción funcional alterada;
- sintaxis JavaScript válida;
- regresión completa y Docker aprobados;
- versión mantenida en 0.45.5 mientras falte la Marca Maestra exacta.
