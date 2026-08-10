# V1.9.0 · Consolidación de superficies núcleo

## Baseline

V1.9 parte exactamente del cierre limpio y certificado de V1.8 en `aa82b32c4e708e10429303f1b6fb7d3f2aed49e9`.

La rama `refactor/v1-8-0-strategic-surfaces` queda congelada como baseline certificada. `main` continúa fuera de alcance.

## Objetivo

Reducir la deuda residual de `app/main.py` en superficies núcleo y transversales que todavía vivían en el composition root, moviendo únicamente HTTP y helpers cohesionados cuando existía una autoridad de dominio clara.

No se modificaron factores, GWP, fórmulas de huella, motor de cálculo ni semántica de reporting.

## Snapshot de partida

- `app/main.py`: **1.583 líneas / 49 rutas**;
- `app/database.py`: **269 líneas**;
- rutas HTTP totales: **344**;
- tablas ORM: **124**;
- suite certificada V1.8: **551 passed, 1 skipped**;
- smoke V1.8: **56 passed, 496 deselected**.

## Cortes completados

V1.9 cerró y certificó, de forma independiente y con `head` limpio entre cortes, las siguientes superficies:

1. **Analytics HTTP** — 3 rutas.
2. **Scenarios HTTP** — 3 rutas.
3. **Verification HTTP** — 5 rutas.
4. **Automations HTTP** — 5 rutas.
5. **Service Account HTTP** — 2 rutas y `_service_usage`.
6. **Customer Onboarding HTTP** — 2 rutas.
7. **Platform Administration HTTP** — 4 rutas.
8. **Document Center HTTP** — 3 rutas.
9. **Readiness / Alistamiento HTTP** — 2 rutas.
10. **Notifications HTTP** — 4 rutas personales.
11. **Portfolio multiempresa HTTP** — 3 rutas.
12. **Executive Portfolio HTTP** — 1 ruta.
13. **Compliance HTTP** — 2 rutas y autoridad definitiva `compliance_score`; Executive Portfolio importa la métrica directamente desde `compliance_web.py`.
14. **Methodology Governance HTTP** — 4 rutas.
15. **Dashboard / core workspace HTTP** — 3 rutas: preferencia de vista, recorrido y dashboard.
16. **Higiene final del composition root** — eliminación de `_lead_complexity` tras demostrar por AST que no tenía consumidores semánticos de runtime; se fijó un contrato persistente para impedir que superficies funcionales regresen a `main.py`.

## Reconciliaciones controladas

- Automations: se corrigió únicamente una fixture que usaba un tipo de automatización inexistente; el valor canónico es `Recordatorio de solicitudes`.
- Compliance: un contrato V1.9 anterior todavía exigía la dependencia transitoria `_compliance_score` dentro de Executive Portfolio. Se actualizó para exigir la autoridad definitiva `from .compliance_web import compliance_score`; no se cambió comportamiento funcional.
- Higiene final: una primera prueba confundió menciones textuales de `_lead_complexity` dentro de tests con usos de runtime. La prueba definitiva usa AST y elimina el helper solo al confirmar cero `Name(..., Load)` semánticos.

## Snapshot final limpio previo a certificación integral

Medido sobre el `head` limpio `05428ec98de0b7a1e86e3db544a3a696ea10b52e` mediante CI canónico `31428807242`:

- archivos Python: **157**;
- líneas Python: **40.163**;
- `app/main.py`: **639 líneas / 3 rutas**;
- `app/database.py`: **269 líneas**;
- rutas HTTP totales: **344**;
- tablas ORM: **124**;
- smoke: **56 passed / 543 deselected**;
- arquitectura: **green**;
- Alembic desde instancia vacía y `SEED_DEMO=false`: **green**.

Las únicas rutas HTTP directas permitidas en `app/main.py` quedan fijadas por `tests/test_v190_composition_root.py`:

- `GET /modulos`;
- `GET /api/health`;
- `GET /api/ready`.

`main.py` queda por tanto como **composition root**: middleware, contexto transversal, utilidades inyectadas, registro de módulos y endpoints de sistema/salud.

## Reglas aplicadas

Cada corte pasó contratos dirigidos, regresión completa, `scripts/audit_architecture.py --enforce` y smoke canónico antes del commit. Los workflows temporales se eliminaron antes de certificar cada `head` limpio. Los cortes sensibles a persistencia se verificaron además mediante el CI canónico con Alembic desde instancia limpia.

No se relajó lógica de producto para satisfacer tests históricos obsoletos; cuando un contrato quedó desactualizado por una transición arquitectónica intencional, se reconcilió el contrato y se volvió a ejecutar la regresión completa.

## Cierre de alcance

El alcance funcional y arquitectónico de V1.9 queda **congelado** con este documento. No se planifican más refactors funcionales dentro del ciclo.

Lo único pendiente después de este cierre documental es la **certificación integral V1.9**, la limpieza de su workflow temporal, la verificación canónica del SHA final limpio y la actualización del PR #22.

El PR V1.9 permanece draft. No se fusiona a V1.8 ni a `main` durante esta certificación.
