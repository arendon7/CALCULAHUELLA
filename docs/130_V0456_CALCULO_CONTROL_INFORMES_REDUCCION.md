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

Se mantienen el recálculo, los resultados por fuente, las alertas y errores del motor, el acceso a trazabilidad y la explicación de las reglas activas.

### 2. Control

Objetivo: convertir el resultado técnico en una versión revisable, aprobable y cerrable.

Superficie:

```text
/control
```

Se mantienen las puertas de calidad, observaciones, respuestas, recomendación independiente, aprobación final, cierre inmutable, reapertura mediante nueva versión, historial formal y auditoría.

### 3. Informes

Objetivo: seleccionar el entregable adecuado y conservar versiones, estado e integridad.

Superficie:

```text
/reportes
```

Se mantienen el informe ejecutivo, informe técnico, memoria de cálculo, generación PDF/Excel, descarga, aprobación, hash y tamaño del archivo.

### 4. Reducción

Objetivo: priorizar medidas por impacto, inversión, ahorro, viabilidad, riesgo, responsable y fecha.

Superficie:

```text
/reduccion
```

Se mantienen la creación y actualización de acciones, metas absolutas o de intensidad, sincronización con el inventario, seguimiento, reducción real y esperada y economía de cada medida.

### 5. Escenarios

Objetivo: comparar portafolios, adopción, cronograma, costo marginal y trayectoria.

Superficie:

```text
/escenarios
```

Se mantienen la configuración, inclusión de medidas, porcentaje de adopción, año de implementación, tasa de descuento, curva de costo marginal, emisiones proyectadas y creación de portafolios.

## Mejoras de experiencia

`app/static/js/cth-outcomes.js` incorpora:

- navegación de cinco etapas con `aria-current="step"`;
- propósito y siguiente acción por etapa;
- eliminación de la navegación de captura al entrar en `/calculos`;
- barras de progreso accesibles;
- trayectorias y curvas marginales enfocables;
- búsqueda local en resultados, documentos, medidas, acciones y observaciones;
- normalización que ignora mayúsculas y tildes.

`app/static/css/cth-outcomes.css` añade recorrido horizontal responsive, contexto de etapa, jerarquía de indicadores, numeración de entregables, herramientas de búsqueda, estados vacíos y foco visible.

## Contratos preservados

No se modifican modelos, migraciones, motor de cálculo, conversiones, factores, GWP, generación documental, permisos, segregación de funciones, estados, rutas ni formularios existentes.

## Archivos

```text
app/static/css/cth-outcomes.css
app/static/css/cth-tokens.css
app/static/js/cth-outcomes.js
app/templates/base.html
tests/test_v0456_outcome_experience.py
.github/workflows/ci.yml
```

## Validación ejecutada

CI terminó en verde para:

- árbol y dependencias;
- Python, shell y JavaScript;
- contrato de marca;
- migraciones Alembic;
- 64 plantillas Jinja;
- regresiones v0.45.x;
- prueba del recorrido de resultados;
- construcción Docker.

## Estado de versión

El bloque funcional está cerrado. La versión permanece en 0.45.5 porque el cierre formal de v0.45.6 sigue condicionado a recuperar, instalar y verificar los cuatro activos exactos de la Marca Maestra v1.
