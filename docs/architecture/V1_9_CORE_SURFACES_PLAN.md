# V1.9.0 · Consolidación de superficies núcleo

## Baseline

V1.9 parte exactamente del cierre limpio y certificado de V1.8 en `aa82b32c4e708e10429303f1b6fb7d3f2aed49e9`.

La rama `refactor/v1-8-0-strategic-surfaces` queda congelada como baseline certificada. `main` continúa fuera de alcance.

## Objetivo

Reducir la deuda residual de `app/main.py` en superficies núcleo y transversales que todavía viven en el composition root, moviendo únicamente HTTP y helpers cohesionados cuando ya exista una autoridad de dominio clara.

No se modifican factores, GWP, fórmulas de huella, motor de cálculo ni semántica de reporting.

## Snapshot de partida

- `app/main.py`: **1.583 líneas / 49 rutas**;
- `app/database.py`: **269 líneas**;
- rutas HTTP totales: **344**;
- tablas ORM: **124**;
- suite certificada V1.8: **551 passed, 1 skipped**;
- smoke V1.8: **56 passed, 496 deselected**.

## Secuencia inicial

1. **Dashboard / Analytics** — inventariar primero la frontera entre dashboard, indicadores y analítica; no mover cálculo.
2. **Scenarios HTTP** — preservar `app/scenarios.py` como autoridad de resumen, MACC y portafolio.
3. **Verification HTTP** — preservar `app/verification.py` como autoridad de paquetes y trazabilidad de verificación.
4. **Automations HTTP** — preservar `app/automations.py` como autoridad de tipos, cadencias y ejecución.
5. **Service account / onboarding / platform settings / document control** — solo después de delimitar dependencias y contratos existentes.
6. Inventario residual y certificación integral V1.9.

## Reglas

Cada corte debe pasar contratos dirigidos, regresión completa, `scripts/audit_architecture.py --enforce`, smoke canónico y Alembic cuando aplique antes del commit. Los workflows temporales se eliminan antes de certificar cada `head` limpio.

El PR V1.9 permanecerá draft. No se fusiona a V1.8 ni a `main` durante el desarrollo.
