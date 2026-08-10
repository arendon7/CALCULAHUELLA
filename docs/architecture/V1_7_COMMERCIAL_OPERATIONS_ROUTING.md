# V1.7 · Commercial Operations HTTP

## Autoridad

`app/commercial_operations_web.py` pasa a ser la autoridad HTTP de operación comercial posterior a la propuesta y al pago. El corte incluye 11 rutas para contratos, órdenes de servicio, cobros recurrentes, cartera y documentos de cobro.

## Helpers cohesionados

También se mueven `_contract_signature_hash`, `_contract_reference` y `_order_reference`, porque solo sirven a este contexto. Customer Success permanece fuera del corte.

## Semántica preservada

No se cambian estados, reglas de firma, renovación, referencias, importes, creación de documentos internos de cobro, gestión de cartera ni auditoría. `format_number`, `parse_date`, permisos y contexto común siguen inyectados desde la composición principal.

## Gates

Los tests históricos V0.16 protegen semilla comercial, firma, renovación, ciclo de órdenes, cobro recurrente y cierre de cartera. El contrato V1.7 protege autoridad HTTP, unicidad de rutas y disponibilidad de la pantalla.
