# V1.6 · Reporting / reduction routing

## Estado previo

La superficie HTTP de reporting ya tiene autoridad en `app/reports_web.py`. Ocho rutas de reducción continuaban embebidas en `app/main.py`.

## Corte materializado

- Las 8 rutas `/reduccion*` pasan a `app/reduction_web.py`.
- `app/main.py` conserva únicamente el registro del módulo y las fachadas/helpers compartidos que ya existían.
- La lógica de portafolio permanece en `app/reduction_portfolio.py`.
- La generación de informes permanece en `app/reports_web.py`, `app/reporting.py`, `app/report_consulting.py` y servicios/repositorios existentes.
- No se modifican fórmulas, emisiones, factores, GWP, cálculos, estados de aprobación ni contenido de reportes.

## Contratos

1. Exactamente 8 rutas HTTP de reducción, sin duplicados.
2. `/reportes` y `/reportes/consultoria` siguen operativos.
3. `/reduccion` y `/api/reduccion/resumen` siguen operativos.
4. Suite V0.48 protege semántica del portafolio y exportación.
5. Suite V0.55 protege reporting consultivo.
6. Suite completa, arquitectura y smoke deben quedar verdes antes del commit.
