# V1.6 · Inventory Context

## Estado previo

Las rutas de organizaciones e inventarios ya estaban separadas en `organizations_web.py` e `inventories_web.py`. La deuda residual era transversal: `main.py` seguía siendo propietario de cuatro helpers de acceso y contexto que se inyectaban a múltiples módulos.

## Corte materializado

`app/inventory_context.py` pasa a ser la autoridad de:

- `get_inventory`;
- `get_source_for_user`;
- `ensure_inventory_editable`;
- `inventory_metrics`.

`app/main.py` importa esas funciones y mantiene las mismas referencias que entrega a los registradores de rutas, por lo que no cambian sus firmas ni contratos.

## Límites

- No se mueven rutas HTTP en este corte.
- No se modifican modelos ORM ni migraciones.
- No se alteran emisiones, factores, GWP, fórmulas ni estados.
- No se modifican `review_gate_summary`, `clone_inventory_version` ni otros helpers de negocio.
- El nuevo módulo consume directamente los modelos canónicos de `app.db.models` y no importa `main.py` ni `database.py`.

## Contratos

1. Inventario y fuente siguen aislados por `organization_id`.
2. Inventarios cerrados/bloqueados conservan HTTP 409.
3. Las métricas conservan total, alcances y serie mensual.
4. `/inventarios`, `/inventario` y el detalle de inventario permanecen operativos.
5. Suite completa, arquitectura y smoke deben quedar verdes antes del commit.
