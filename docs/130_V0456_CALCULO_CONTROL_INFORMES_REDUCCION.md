# V0.45.6 — Cálculo, control, informes y reducción

## Propósito

Transformar el resultado técnico del inventario en un recorrido comprensible de decisión, sin modificar datos, factores, fórmulas, permisos, estados ni endpoints.

```text
Cálculo → Control → Informes → Reducción → Escenarios
```

## Etapas

### Cálculo — `/calculos`

Confirma que datos, conversiones, factores y GWP produzcan resultados trazables. Se mantienen recálculo, resultados por fuente, alertas, errores, acceso a trazabilidad y reglas activas.

### Control — `/control`

Convierte el resultado técnico en una versión revisable, aprobable y cerrable. Se mantienen puertas de calidad, observaciones, respuestas, recomendación independiente, aprobación, cierre inmutable, nueva versión e historial de auditoría.

### Informes — `/reportes`

Selecciona el entregable y conserva versiones, estado e integridad. Se mantienen informe ejecutivo, informe técnico, memoria de cálculo, generación PDF/Excel, descarga, aprobación, hash y tamaño.

### Reducción — `/reduccion`

Prioriza medidas por impacto, inversión, ahorro, viabilidad, riesgo, responsable y fecha. Se mantienen acciones, metas, sincronización, seguimiento, reducción real/esperada y economía de cada medida.

### Escenarios — `/escenarios`

Compara portafolios, adopción, cronograma, costo marginal y trayectoria. Se mantienen configuración, medidas, adopción, año, tasa de descuento, curva marginal, emisiones proyectadas y creación de portafolios.

## Mejoras de experiencia

`app/static/js/cth-outcomes.js` incorpora:

- navegación de cinco etapas con `aria-current="step"`;
- propósito y siguiente acción por etapa;
- sustitución de la navegación de captura al entrar en `/calculos`;
- barras de progreso accesibles;
- trayectorias y curvas marginales enfocables;
- búsqueda local en resultados, documentos, medidas, acciones y observaciones;
- normalización que ignora mayúsculas y tildes.

`app/static/css/cth-outcomes.css` añade recorrido responsive, contexto de etapa, jerarquía de indicadores, numeración de entregables, herramientas de búsqueda, estados vacíos y foco visible.

## Contratos preservados

No se modifican modelos, migraciones, motor, conversiones, factores, GWP, generación documental, permisos, segregación de funciones, estados, rutas ni formularios.

## Archivos

```text
app/static/css/cth-outcomes.css
app/static/css/cth-tokens.css
app/static/js/cth-outcomes.js
app/templates/base.html
tests/test_v0456_outcome_experience.py
.github/workflows/ci.yml
```

## Validación

CI terminó en verde para árbol, dependencias, Python, shell, JavaScript, contrato de marca, migraciones, 64 plantillas Jinja, regresiones v0.45.x, prueba del recorrido y Docker.

## Estado

El bloque funcional está cerrado. La versión permanece en 0.45.5 porque el cierre formal de v0.45.6 sigue condicionado a recuperar e instalar los cuatro activos exactos de la Marca Maestra v1.
