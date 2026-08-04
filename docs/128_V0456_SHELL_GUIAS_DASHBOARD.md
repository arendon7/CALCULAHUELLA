# V0.45.6 — Shell, experiencias guiadas y dashboard

## Objetivo

Aplicar el Frontend Kit v1 a las superficies de mayor frecuencia sin alterar rutas, permisos, modelos, migraciones, cálculos ni datos.

## Shell interno

Se incorporaron:

- contexto visible de rol y foco de trabajo;
- nombres accesibles para los grupos de navegación;
- `aria-current="page"` para el módulo activo;
- señal visual lateral del módulo actual;
- nombre de la organización visible en móvil;
- sidebar responsive con fondo modal;
- bloqueo del desplazamiento de fondo;
- entrada y retorno controlados del foco;
- cierre al regresar a escritorio;
- semántica mejorada para ayuda, notificaciones, sesión y mensajes de estado.

Archivos principales:

```text
app/static/css/cth-shell.css
app/static/js/cth-shell.js
app/templates/base.html
```

## Puesta en marcha

La experiencia ahora separa claramente:

1. estado general;
2. siguiente actividad;
3. resultado esperado;
4. progreso cuantitativo;
5. gestión administrativa de cada actividad.

Se añadieron `progressbar`, títulos vinculados, etapa actual semántica y diseño responsive para la ruta de seis actividades.

## Primer inventario guiado

El asistente de cuatro pasos conserva la lógica original y añade:

- navegación lateral sticky en escritorio;
- navegación compacta en tablet y móvil;
- relación explícita entre indicadores y paneles;
- progreso anunciado y actualizado;
- foco claro en selección de paquetes iniciales;
- acciones inferiores persistentes;
- tarjetas y ayudas visuales gobernadas por los tokens oficiales.

Archivos principales:

```text
app/static/css/cth-guided.css
app/static/js/cth-guided.js
app/templates/onboarding.html
app/templates/inventory_form.html
```

## Dashboard

El dashboard mantiene todos los datos y enlaces, pero ordena la experiencia en este nivel de prioridad:

1. completar la puesta en marcha cuando aplique;
2. comprender el rol y la vista actual;
3. ejecutar la siguiente acción del flujo principal;
4. revisar indicadores de emisiones;
5. analizar distribución, calidad, fuentes y solicitudes.

También se incorporaron descripciones accesibles para progreso, distribución por alcance, completitud e indicadores principales.

Archivo principal:

```text
app/static/css/cth-dashboard.css
app/templates/dashboard.html
```

## Controles automáticos

CI valida ahora:

- sintaxis Python y shell;
- sintaxis de `app.js`, `cth-shell.js` y `cth-guided.js`;
- contrato de marca;
- migraciones Alembic;
- compilación de plantillas Jinja;
- regresiones v0.45.x;
- `tests/test_v0456_guided_experience.py`;
- construcción Docker.

## Límite vigente

Los SVG legacy continúan temporalmente referenciados porque los cuatro PNG exactos de la Marca Maestra aún no se han materializado. Este bloque no redibuja ni sustituye el logo y no habilita todavía el cambio de versión a 0.45.6.
