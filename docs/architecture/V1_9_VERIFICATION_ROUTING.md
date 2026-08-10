# V1.9 · Verification HTTP

## Autoridad

`app/verification_web.py` pasa a ser la autoridad HTTP de cinco contratos: portal, alta/respuesta/cierre de hallazgos y generación del paquete de verificación.

## Dominio preservado

`app/verification.py` conserva la generación del paquete verificable. El gate de revisión sigue inyectando `review_gate_summary`; no se alteran cálculos, evidencia, decisiones, permisos ni contenidos del manifiesto.

## Acceso

Portal y paquete permanecen restringidos a auditor externo, revisión o aprobación. Alta/cierre exigen `external_audit`; la respuesta conserva los roles de gestión de inventario, provisión de datos o revisión.

## Gates

Los contratos históricos V0.7 protegen login del verificador y ciclo completo del hallazgo. V0.8 protege el ZIP de verificación con manifiesto, cálculos y hallazgos. El contrato V1.9 protege autoridad y unicidad HTTP.
