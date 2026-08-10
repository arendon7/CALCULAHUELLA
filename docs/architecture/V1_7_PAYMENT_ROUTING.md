# V1.7 · Proposal Acceptance / Payments HTTP

## Corte 2 de Commercial / Payments

`app/payment_web.py` pasa a ser la autoridad HTTP de cinco contratos:

- aceptar propuesta;
- rechazar propuesta;
- mostrar pago;
- confirmar pago demostrativo;
- webhook de pago.

## Side effects preservados

El corte mantiene literalmente la semántica previa: hash de aceptación, creación idempotente de `PaymentTransaction`, pago demo, creación/asociación de organización, suscripción, registro administrativo de cobro, onboarding inicial y estado `Ganado` del lead.

## Seguridad y contrato FastAPI

`PaymentWebhookPayload` queda a nivel de módulo, antes del registrador de rutas, para que FastAPI/Pydantic resuelvan el body JSON como modelo real. El webhook conserva `hmac.compare_digest`, secreto obligatorio, verificación del importe y normalización de estados. Un webhook con JSON válido pero sin firma debe responder HTTP 401 antes de consultar la transacción.

## Gates

El test histórico `test_commercial_proposal_acceptance_and_demo_payment` protege el flujo de extremo a extremo. Los contratos V1.7 protegen autoridad HTTP, unicidad, resolución del payload y rechazo de webhook sin firma.
