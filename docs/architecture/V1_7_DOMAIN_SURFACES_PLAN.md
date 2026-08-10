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
5. **Commercial Operations HTTP — cerrado.** Once rutas de contratos, órdenes de servicio, cobros recurrentes, cartera y documentos de cobro quedaron en `commercial_operations_web.py`. El producto fue materializado en `f00a9fe3655a948a25031f0d73dae71d92a97854` y el materializador temporal se retiró en `ad4572a737b6e9aaef5bc7f63332392b8462fb43`.

Todos los cortes anteriores pasaron contratos dirigidos, regresión completa, barrera arquitectónica y smoke antes de sus commits de producto. Los materializadores temporales fueron retirados después de cada corte.

## Secuencia restante

1. Customer Success HTTP, usando los contratos históricos V0.17 como gate funcional.
2. SaaS Administration residual, solo después de certificar Customer Success.
3. Inventario final de rutas/hotspots residuales.
4. Certificación integral V1.7 y evidencia persistente.

## Reglas

Cada corte debe pasar contratos dirigidos, suite completa, `scripts/audit_architecture.py --enforce`, smoke canónico y Alembic cuando aplique antes del commit de producto. Los workflows temporales se eliminan antes de certificar el `head` limpio.

No se modifican factores, GWP, fórmulas de huella o semántica de reporting salvo que un corte posterior lo declare explícitamente y tenga contratos específicos.
