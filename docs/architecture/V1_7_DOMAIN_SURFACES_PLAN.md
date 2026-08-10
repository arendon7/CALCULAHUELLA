# V1.7.0 · Consolidación de dominios operativos residuales

## Baseline

V1.7 parte exactamente del cierre certificado V1.6 en `092122afec70bb32f825d087b89a0401249f438a`.

La V1.6 permanece congelada en `refactor/v1-6-0-consolidation`; `main` continúa fuera de alcance.

## Objetivo

Reducir deuda residual de `app/main.py` por dominios cohesivos, sin reescribir reglas de negocio, fórmulas o contratos certificados.

## Orden de trabajo

1. Supply Chain / Scope 3 HTTP.
2. Support HTTP.
3. Commercial / Payments en cortes separados por riesgo.
4. Customer Success / SaaS residual, solo si los cortes anteriores quedan certificados.
5. Certificación integral V1.7.

## Reglas

Cada corte debe pasar contratos dirigidos, suite completa, `scripts/audit_architecture.py --enforce`, smoke canónico y Alembic cuando aplique antes del commit de producto. Los workflows temporales se eliminan antes de certificar el `head` limpio.

No se modifican factores, GWP, fórmulas de huella o semántica de reporting salvo que un corte posterior lo declare explícitamente y tenga contratos específicos.
