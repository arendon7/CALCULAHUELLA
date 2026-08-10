# V1.9 · Compliance HTTP

## Autoridad

`app/compliance_web.py` pasa a ser la autoridad de `/cumplimiento`, su actualización y `compliance_score`. El helper deja `main.py` y Executive Portfolio lo importa directamente.

## Semántica preservada

`No aplica` se excluye del denominador; `Cumple` pesa 100, `Parcial` 50 y `Pendiente`/`No cumple` 0. La actualización conserva estados válidos, propietario, evidencia, notas, `updated_by` y auditoría.

## Acceso e integridad

La lectura exige `view_compliance`; la mutación `manage_compliance`. La evidencia opcional debe pertenecer al mismo inventario de la evaluación y toda evaluación se resuelve dentro de la organización activa.

## Reconciliación

El contrato V1.9 de Executive Portfolio se actualiza desde la dependencia transitoria `_compliance_score` hacia la autoridad definitiva `compliance_web.compliance_score`; no se altera ningún comportamiento funcional.

## Gates

V0.13 protege que Consultor pueda actualizar y Verificador sea solo lectura. El contrato V1.9 protege autoridad HTTP, unicidad y la fórmula exacta del score.
