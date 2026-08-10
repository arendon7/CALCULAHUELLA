# V1.9 · Certificación final

## Estado

**CERTIFICADA** sobre la rama `refactor/v1-9-0-core-surfaces`. Esta acta fue generada únicamente después de superar todos los gates integrales de V1.9.

## Baseline y alcance

- Baseline V1.8: `aa82b32c4e708e10429303f1b6fb7d3f2aed49e9`.
- `main` permanece fuera de alcance y no fue modificado por la promoción de esta rama.
- El PR #22 continúa draft.

## Evidencia integral

- Suite completa: **598 passed / 1 skipped**.
- Smoke: **56 passed / 543 deselected**.
- Arquitectura: **green**.
- Estructura canónica sin `.git`: **green**.
- Alembic desde instancia vacía con `SEED_DEMO=false`: **green**.
- Contratos HTTP: **344 únicos**, sin duplicados `(method, path)`.
- Tablas ORM: **124**.
- Archivos Python: **157**.
- Líneas Python: **40163**.
- `app/main.py`: **639 líneas / 3 rutas directas**.

## Composition root

Las únicas rutas HTTP directas permitidas en `app/main.py` son:

- `GET /api/health`
- `GET /api/ready`
- `GET /modulos`

El resto de superficies HTTP tiene autoridad modular. `tests/test_v190_composition_root.py` fija esta frontera de forma persistente.

## Superficies cerradas en V1.9

- Analytics
- Scenarios
- Verification
- Automations
- Service Account
- Customer Onboarding
- Platform Administration
- Document Center
- Readiness / Alistamiento
- Notifications
- Portfolio multiempresa
- Executive Portfolio
- Compliance
- Methodology Governance
- Dashboard / core workspace
- final dead-code hygiene

## Higiene de workflows

Durante esta certificación no existían materializadores ni diagnósticos residuales. El único workflow temporal presente es `certify-v19-final.yml`, que debe eliminarse inmediatamente después de esta acta. Tras esa limpieza, el conjunto permanente canónico de esta rama vuelve a ser exclusivamente:

- `.github/workflows/ci.yml`
- `.github/workflows/iteration4-stabilization.yml`
- `.github/workflows/package-mac-selfcontained.yml`
- `.github/workflows/pages.yml`

## Resultado arquitectónico

V1.9 parte de `app/main.py` **1.583 líneas / 49 rutas** en V1.8 y termina la certificación con **639 líneas / 3 rutas directas**, manteniendo **344 contratos HTTP** totales y **124 tablas ORM**.

La rama queda lista para limpieza del workflow de certificación y un último CI canónico sobre el SHA limpio. No se autoriza merge automático ni promoción a `main` mediante esta acta.
