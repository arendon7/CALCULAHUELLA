# V1.9 · Readiness HTTP

## Autoridad

`app/readiness_web.py` pasa a ser la autoridad HTTP de dos contratos: panel de alistamiento comercial y actualización de cada elemento.

## Semántica preservada

Se conserva el score por estados (`Completado` 100, `En progreso` 50, `Pendiente`/`Bloqueado` 0), agrupación por categoría, responsable, fecha objetivo, notas y auditoría.

## Acceso e aislamiento

Ambas rutas continúan exigiendo `manage_readiness`; cada elemento se filtra por `organization_id`. En la matriz vigente esa capacidad pertenece al rol Administrador.

## Gates

V0.13 protege lectura, actualización persistente y `updated_by`. El contrato V1.9 protege autoridad HTTP, unicidad y restricción por capacidad.
