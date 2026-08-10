# V1.6 · Inventory Lifecycle

## Objetivo

Separar de `main.py` la creación de una nueva versión corregible a partir de un inventario cerrado, sin alterar rutas, reglas de aprobación ni cálculo.

## Autoridad nueva

`app/inventory_lifecycle.py` contiene:

- `next_inventory_version`;
- `clone_inventory_version`.

`review_web.py` continúa recibiendo `clone_inventory_version` por la misma inyección existente desde `main.py`.

## Semántica preservada

- el inventario original no se modifica;
- la nueva versión referencia `parent_inventory_id`;
- versión `-rN` avanza de manera determinista;
- estado nuevo `Borrador`, etapa `Corrección`, `locked=False`;
- se copian sedes, fuentes, asignaciones, evidencias, datos de actividad, indicadores, acciones, metas, escenarios y campañas de proveedores según la implementación previa;
- se registra una observación `Mayor` con el motivo de reapertura;
- `refresh_progress` y `recalculate_inventory` siguen siendo las autoridades existentes: no se duplican fórmulas ni reglas.

## Límites

No se modifican `/control/inventario/reabrir`, aprobación/cierre, modelos, migraciones, factores, GWP ni fórmulas.
