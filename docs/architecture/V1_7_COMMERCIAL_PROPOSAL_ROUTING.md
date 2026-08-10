# V1.7 · Commercial proposal HTTP

## Corte 1 de Commercial / Payments

Se extraen a `app/commercial_web.py` únicamente las superficies de gestión y consulta de propuestas:

- centro comercial;
- estado del prospecto;
- creación de propuesta;
- marcado como enviada;
- vista pública de propuesta.

## Fuera de alcance

Aceptación/rechazo, creación de `PaymentTransaction`, pantalla de pago, confirmación y webhook permanecen en `app/main.py` para un segundo corte independiente.

## Regla de riesgo

La vista pública puede leer la última transacción asociada, pero este módulo no crea ni concilia pagos. El test histórico `test_commercial_proposal_acceptance_and_demo_payment` debe seguir verde para demostrar compatibilidad end-to-end.
