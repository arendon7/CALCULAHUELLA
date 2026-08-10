# V1.9 · Customer Onboarding HTTP

## Autoridad

`app/customer_onboarding_web.py` pasa a ser la autoridad HTTP de dos contratos: vista de onboarding y actualización de actividades.

## Dominio preservado

`app/onboarding_experience.py` conserva `onboarding_summary`. No se alteran score, estados (`Pendiente`, `En progreso`, `Completado`, `Bloqueado`), responsable, vencimiento ni marca temporal de completado.

## Acceso e aislamiento

La lectura sigue disponible al usuario autenticado de la organización. La mutación conserva la regla histórica `can_manage_org` o `can_manage_inventory`, y cada ítem se filtra por `organization_id`.

## Gates

El contrato histórico `test_onboarding_item_can_be_completed` protege persistencia y `completed_at`. El contrato V1.9 protege autoridad HTTP, unicidad y disponibilidad para Cliente.
