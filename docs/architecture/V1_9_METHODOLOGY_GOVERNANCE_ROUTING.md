# V1.9 · Methodology Governance HTTP

## Autoridad

`app/methodology_governance_web.py` pasa a ser la autoridad HTTP del panel de gobierno metodológico, alta de versiones, aprobación y snapshots por inventario.

## Semántica preservada

Las versiones nacen en `Borrador`, conservan huella SHA-256 sobre nombre/versión/referencia/notas y registran organismo emisor y fechas. La aprobación mantiene `approved_by`/`approved_at`. Los snapshots congelan metodología, versión, GWP, enfoque de consolidación, materialidad y política del inventario.

## Acceso e aislamiento

Las cuatro rutas continúan exigiendo `manage_methodology_governance`. Releases y snapshots permanecen limitados a la organización activa; el inventario se resuelve mediante `get_inventory`.

## Gates

V0.13 protege el lifecycle completo: creación por Consultor, aprobación por Revisor y snapshot vinculado a la versión aprobada. El contrato V1.9 protege autoridad HTTP, unicidad y permisos.
