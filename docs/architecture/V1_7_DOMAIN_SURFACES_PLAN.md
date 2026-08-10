# V1.7.0 · Consolidación de dominios operativos residuales

## Baseline

V1.7 parte exactamente del cierre certificado V1.6 en `092122afec70bb32f825d087b89a0401249f438a`.

La V1.6 permanece congelada en `refactor/v1-6-0-consolidation`; `main` continúa fuera de alcance.

## Objetivo

Reducir deuda residual de `app/main.py` por dominios cohesivos, sin reescribir reglas de negocio, fórmulas o contratos certificados.

## Estado materializado

1. **Supply Chain / Scope 3 HTTP — cerrado.** La captura interna, solicitudes a proveedores, portal público, evidencia, revisión y sincronización tienen autoridad HTTP dedicada.
2. **Support HTTP — cerrado.** SLA, asignación, conversación, notas internas y estados conservan `support_workflow.py` como autoridad de negocio.
3. **Commercial Proposal HTTP — cerrado.** Centro comercial, leads, creación/envío de propuesta y vista pública quedaron separados de aceptación y pagos.
4. **Proposal Acceptance / Payments HTTP — cerrado.** Aceptación/rechazo, pago demo y webhook quedaron aislados en `payment_web.py`; `PaymentWebhookPayload` permanece a nivel de módulo para resolución correcta de FastAPI/Pydantic.
5. **Commercial Operations HTTP — cerrado.** Once rutas de contratos, órdenes de servicio, cobros recurrentes, cartera y documentos de cobro quedaron en `commercial_operations_web.py`.
6. **Customer Success HTTP — cerrado.** Ocho rutas de perfil, salud, hitos, compromisos y renovación quedaron en `customer_success_web.py`; `customer_success.py` conserva la autoridad de métricas y reglas de salud/renovación. Producto materializado en `e21d49e1933c15e0ebff4153f4f11b11a9e3aaca`, materializador retirado en `90f61b93be6d21257329bcc81b6182614cff845d` y CI canónico limpio `31405709678` verde.
7. **SaaS Administration HTTP — cerrado.** Cuatro rutas de panel, planes, suscripciones y estado de cobros quedaron en `saas_admin_web.py`. Producto materializado en `8e41a167b97bb715822fe734c5d638ead3883949`, materializador retirado en `08c0e044959f1571b274aea6c7b40bfea8a26d4d` y CI canónico limpio `31406108879` verde.

Todos los cortes pasaron contratos dirigidos, regresión completa, barrera arquitectónica y smoke antes de sus commits de producto. Los materializadores temporales fueron retirados después de cada corte.

## Inventario residual al cierre de alcance

Snapshot canónico sobre `08c0e044959f1571b274aea6c7b40bfea8a26d4d`:

- 138 archivos Python;
- 39.755 líneas Python;
- 344 rutas HTTP totales;
- 124 tablas ORM;
- `app/database.py`: 269 líneas;
- `app/main.py`: **2.224 líneas y 81 rutas**;
- smoke: **56/56**.

Hotspots principales todavía presentes en `main.py`:

- `dashboard`: 52 líneas;
- `review_gate_summary`: 41 líneas;
- `_service_usage`: 36 líneas;
- `climate_scenario_create`: 34 líneas;
- `automation_create`: 33 líneas;
- `create_indicator`: 31 líneas;
- `verification_portal`: 31 líneas;
- `climate_requirement_create`: 29 líneas;
- `update_consolidation_finding`: 28 líneas;
- `update_release_gate`: 28 líneas.

Estos residuos pertenecen a otros bounded contexts y no se incorporan artificialmente a V1.7. La siguiente ola debe tratarse como un ciclo apilado separado, con prioridad sugerida en Impact Intelligence, Climate Risk/Disclosure, consolidación/release governance y superficies transversales restantes.

## Cierre de alcance V1.7

La secuencia planificada quedó completada. El único trabajo restante de V1.7 es la **certificación integral final**, persistencia del acta técnica, limpieza del workflow de certificación y CI canónico sobre el SHA final limpio.

## Reglas

Cada corte debe pasar contratos dirigidos, suite completa, `scripts/audit_architecture.py --enforce`, smoke canónico y Alembic cuando aplique antes del commit de producto. Los workflows temporales se eliminan antes de certificar el `head` limpio.

No se modifican factores, GWP, fórmulas de huella o semántica de reporting salvo que un ciclo posterior lo declare explícitamente y tenga contratos específicos.
