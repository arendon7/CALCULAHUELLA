# V1.7 · Supply Chain / Scope 3 HTTP

## Baseline

V1.7 parte de la V1.6 certificada. `app/supply_chain.py` ya contiene la autoridad de screening, validación, cálculo de respuestas, calidad, duplicados y sincronización de la fuente de proveedor.

## Corte

Las 12 rutas del flujo de cadena de valor pasan de `app/main.py` a `app/supply_chain_web.py` como una única superficie cohesiva:

- screening y resumen Scope 3;
- proveedores, campañas y solicitudes;
- renovación del enlace seguro;
- portal público del proveedor;
- carga de evidencia;
- revisión y sincronización;
- descarga de evidencia;
- plantilla XLSX.

## Regla crítica

El corte mueve HTTP, no lógica de dominio. `app/supply_chain.py`, `scope3_catalog.py`, validación de archivos, almacenamiento y auditoría conservan sus contratos previos.

## Gates

- `tests/test_iteration6_scope3_supply_chain.py` protege las 15 categorías, screening, portal, incompatibilidad de unidades, duplicados y workbook.
- `tests/test_v170_supply_chain_routing.py` protege autoridad HTTP y unicidad de las 12 rutas.
- suite completa, arquitectura y smoke deben quedar verdes antes del commit.
