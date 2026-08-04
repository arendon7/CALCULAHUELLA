# V0.45.6 — Cálculo, control, informes y reducción

## Propósito

Transformar el resultado técnico del inventario en un recorrido comprensible de decisión, sin modificar datos, factores, fórmulas, permisos, estados ni endpoints.

El flujo consolidado es:

```text
Cálculo → Control → Informes → Reducción → Escenarios
```

## Etapas

### 1. Cálculo

Objetivo: confirmar que los datos, conversiones, factores y GWP producen resultados trazables.

Superficie:

```text
/calculos
```

Se mantienen:

- recálculo del inventario;
- resultados por fuente;
- alertas y errores del motor;
- acceso a trazabilidad por fuente;
- explicación de las reglas activas.

### 2. Control

Objetivo: convertir el resultado técnico en una versión revisable, aprobable y cerrable.

Superficie:

```text
/control
```

Se mantienen:

- puertas de calidad;
- observaciones y respuestas;
- recomendación independiente;
- aprobación final;
- cierre inmutable;
- reapertura mediante nueva versión;
- historial formal y auditoría.

### 3. Informes

Objetivo: seleccionar el entregable adecuado y conservar versiones, estado e integridad.

Superficie:

```text
/reportes
```

Se mantienen:

- informe ejecutivo;
- informe técnico;
- memoria de cálculo;
- generación de PDF y Excel;
- descarga;
- aprobación del artefacto;
- hash y tamaño del archivo.

### 4. Reducción

Objetivo: priorizar medidas por impacto, inversión, ahorro, viabilidad, riesgo, responsable y fecha.

Superficie:

```text
/reduccion
```

Se mantienen:

- creación y actualización de acciones;
- metas absolutas o de intensidad;
- sincronización con el inventario;
- seguimiento de avance;
- reducción real y esperada;
- economía de cada medida.

### 5. Escenarios

Objetivo: comparar portafolios, adopción, cronograma, costo marginal y trayectoria.

Superficie:

```text
/escenarios
```

Se mantienen:

- configuración de escenarios;
- inclusión de medidas;
- porcentaje de adopción;
- año de implementación;
- tasa de descuento;
- curva de costo marginal;
- emisiones proyectadas;
- creación de nuevos portafolios.

## Mejoras de experiencia

### Navegación de resultados

`app/static/js/cth-outcomes.js` inserta una navegación de cinco etapas con:

- orden visible;
- `aria-current="step"`;
- textos de propósito;
- acción recomendada hacia la siguiente etapa;
- eliminación de la navegación de captura al entrar en `/calculos`, evitando duplicidad.

### Lectura de progreso

Las barras existentes reciben progresivamente:

- `role="progressbar"`;
- valores mínimo, máximo y actual;
- nombre accesible basado en la tarjeta o medida;
- navegación mediante teclado.

Las curvas marginales y trayectorias se convierten en grupos enfocados con una descripción derivada de su contenido visible.

### Búsqueda local

Sin modificar el backend se habilita búsqueda en:

- resultados por fuente;
- documentos generados;
- medidas del escenario;
- acciones de reducción;
- observaciones de control.

La normalización ignora mayúsculas y tildes. El filtro solo afecta la visualización y nunca elimina datos.

### Jerarquía visual

`app/static/css/cth-outcomes.css` incorpora:

- recorrido horizontal responsive;
- contexto de la etapa;
- énfasis consistente de indicadores;
- numeración de entregables;
- herramientas de búsqueda;
- estados vacíos;
- foco visible en medidas, observaciones y trayectorias.

## Contratos preservados

No se modifican:

- modelos SQLAlchemy;
- migraciones;
- cálculo de emisiones;
- conversiones;
- factores ni GWP;
- generación de documentos;
- permisos y segregación de funciones;
- estados de inventario;
- rutas y formularios existentes.

## Archivos

```text
app/static/css/cth-outcomes.css
app/static/css/cth-tokens.css
app/static/js/cth-outcomes.js
app/templates/base.html
tests/test_v0456_outcome_experience.py
.github/workflows/ci.yml
```

## Criterio de aceptación

- navegación visible en las cinco rutas;
- una sola navegación principal en `/calculos`;
- acciones operativas intactas;
- filtros locales sin cambios de datos;
- progreso y trayectorias accesibles;
- sintaxis JavaScript válida;
- plantillas Jinja compiladas;
- regresión y Docker aprobados.

## Validación ejecutada

La ejecución de CI asociada a esta fase terminó en verde:

- árbol fuente;
- dependencias;
- Python y shell;
- JavaScript, incluido `cth-outcomes.js`;
- contrato de marca;
- migraciones Alembic;
- 64 plantillas Jinja;
- regresiones v0.45.x;
- prueba del recorrido de resultados;
- construcción Docker.

## Estado de versión

Esta integración no eleva por sí sola la versión a 0.45.6. El cierre formal sigue bloqueado hasta recuperar, instalar y verificar los cuatro activos exactos de la Marca Maestra v1.
