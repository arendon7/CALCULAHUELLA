# V1.9 · Portfolio HTTP

## Autoridad

`app/portfolio_web.py` pasa a ser la autoridad HTTP de tres contratos multiempresa: vista de portafolio, cambio de organización activa y creación de organización.

## Semántica preservada

Se conserva selección de inventario más reciente, `demo_story`, validación de membresía activa, `active_org_id`, auditoría del cambio de contexto y creación de membresía `Administrador` para la organización nueva.

## Permisos

La vista requiere `manage_portfolio`. La creación mantiene la barrera adicional `manage_org`; por tanto, acceso al portafolio no equivale a permiso para crear organizaciones.

## Gates

Los contratos históricos protegen cambio de contexto multiempresa y alta de organización/membresía. El contrato V1.9 protege autoridad HTTP, unicidad y acceso por capacidad.
