# V0.45.6 — Cálculo, control, informes y reducción

## Propósito

Transformar el resultado técnico del inventario en un recorrido comprensible de decisión, sin modificar datos, factores, fórmulas, permisos, estados ni endpoints.

```text
Cálculo → Control → Informes → Reducción → Escenarios
```

## Etapas

### Cálculo — `/calculos`
Confirma que datos, conversiones, factores y GWP produzcan resultados trazables. Conserva recálculo, resultados por fuente, alertas, errores, trazabilidad y reglas activas.

### Control — `/control`
Convierte el resultado en una versión revisable, aprobable y cerrable. Conserva puertas de calidad, observaciones, recomendación independiente, aprobación, cierre inmutable y auditoría.

### Informes — `/reportes`
Selecciona entregables y conserva versiones, estado e integridad. Conserva informes ejecutivo/técnico, memoria de cálculo, generación, descarga, aprobación y hashes.

### Reducción — `/reduccion`
Prioriza medidas por impacto, inversión, ahorro, viabilidad, riesgo, responsable y fecha. Conserva acciones, metas, sincronización y seguimiento.

### Escenarios — `/escenarios`
Compara portafolios, adopción, cronograma, costo marginal y trayectoria. Conserva configuración, medidas, tasa de descuento, curva marginal y emisiones proyectadas.

## Mejoras

`app/static/js/cth-outcomes.js` incorpora navegación de cinco etapas, `aria-current="step"`, propósito y siguiente acción, barras accesibles, trayectorias enfocables y búsqueda local tolerante a mayúsculas y tildes.

`app/static/css/cth-outcomes.css` añade recorrido responsive, contexto de etapa, jerarquía de indicadores, numeración de entregables, herramientas de búsqueda, estados vacíos y foco visible.

## Contratos preservados

No se modifican modelos, migraciones, motor, conversiones, factores, GWP, generación documental, permisos, estados, rutas ni formularios.

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

CI aprobó árbol, dependencias, Python, shell, JavaScript, contrato de marca, migraciones, 64 plantillas Jinja, regresiones v0.45.x, prueba del recorrido y Docker.

## Estado

Bloque funcional cerrado. La versión permanece en 0.45.5 hasta recuperar e instalar los cuatro activos exactos de la Marca Maestra v1.
