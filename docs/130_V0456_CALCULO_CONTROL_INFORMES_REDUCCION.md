# V0.45.6 — Cálculo, control, informes y reducción

## Propósito

Transformar el resultado técnico del inventario en un recorrido comprensible de decisión, sin modificar datos, factores, fórmulas, permisos, estados ni endpoints.

```text
Cálculo → Control → Informes → Reducción → Escenarios
```

## Etapas

- **Cálculo — `/calculos`:** confirma resultados trazables y conserva recálculo, alertas, errores y acceso por fuente.
- **Control — `/control`:** conserva puertas de calidad, observaciones, recomendación, aprobación, cierre y auditoría.
- **Informes — `/reportes`:** conserva entregables ejecutivo/técnico, memoria, generación, descarga, aprobación e integridad.
- **Reducción — `/reduccion`:** conserva acciones, metas, inversión, ahorro, responsables, fechas y seguimiento.
- **Escenarios — `/escenarios`:** conserva portafolios, adopción, cronograma, costo marginal y trayectoria.

## Mejoras

`app/static/js/cth-outcomes.js` incorpora navegación de cinco etapas, `aria-current="step"`, orientación contextual, barras accesibles, trayectorias enfocables y búsqueda local tolerante a mayúsculas y tildes.

`app/static/css/cth-outcomes.css` añade recorrido responsive, jerarquía de indicadores, numeración de entregables, herramientas de búsqueda, estados vacíos y foco visible.

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
