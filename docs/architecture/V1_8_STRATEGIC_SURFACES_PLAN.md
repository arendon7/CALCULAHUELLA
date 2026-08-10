# V1.8.0 · Consolidación de superficies estratégicas

## Baseline

V1.8 parte exactamente del cierre limpio y certificado de V1.7 en `d015f21af67bc834d72b1dd6cd97d6082efe04c5`.

La rama `refactor/v1-7-0-domain-surfaces` queda congelada como baseline certificada. `main` continúa fuera de alcance.

## Objetivo

Reducir la deuda residual de `app/main.py` en bounded contexts estratégicos que ya cuentan con lógica de dominio separada, moviendo únicamente sus superficies HTTP y helpers cohesionados.

No se reescriben modelos climáticos, fórmulas de impacto, factores, GWP, motor de cálculo, semántica de reporting ni reglas de negocio salvo que un corte posterior lo declare de manera explícita y tenga contratos propios.

## Cortes materializados

1. **Impact Intelligence HTTP — cerrado.** Cinco rutas pasaron a `app/impact_intelligence_web.py`; `app/impact_intelligence.py` conserva métricas, snapshots, benchmarks y comparación de portafolio.
2. **Climate Risk HTTP — cerrado.** Nueve rutas pasaron a `app/climate_risk_web.py`; `app/climate_risk.py` conserva evaluación, scoring, controles y estados.
3. **Climate Disclosure HTTP — cerrado.** Once rutas pasaron a `app/climate_disclosure_web.py`; `app/climate_disclosure.py` conserva escenarios, divulgación, comité y generación del board pack.
4. **Consolidation / Release Governance HTTP — cerrado.** Siete rutas pasaron a `app/consolidation_web.py`; `app/consolidation.py` y `app/architecture.py` conservan readiness, resumen, exportación y snapshot arquitectónico.

Todos los cortes anteriores pasaron contratos dirigidos, regresión completa, barrera arquitectónica y smoke antes de sus commits de producto. Cada materializador temporal fue retirado antes de certificar el `head` limpio.

## Snapshot limpio previo a certificación

`head`: `490551721e57d750c60e4254b04a7db840487fe5`  
CI canónico: `31408913218` — **success**.

- archivos Python: **142**;
- líneas Python: **39.867**;
- rutas HTTP: **344**;
- tablas ORM: **124**;
- `app/main.py`: **1.583 líneas / 49 rutas**;
- `app/database.py`: **269 líneas**;
- smoke: **56 passed / 496 deselected**;
- Alembic desde instancia limpia: PASS.

## Deuda residual deliberadamente diferida

Los residuos principales de `app/main.py` ya no pertenecen al alcance estratégico V1.8 y se difieren a un ciclo apilado V1.9 para evitar *scope creep*:

- Dashboard y analítica/indicadores;
- escenarios;
- verificación;
- automatizaciones;
- cuenta de servicio y suscripción;
- onboarding;
- configuración de plataforma;
- control documental y otras superficies transversales.

Hotspots representativos todavía presentes: `dashboard` (52 líneas), `review_gate_summary` (41), `_service_usage` (36), `automation_create` (33), `create_indicator` (31), `verification_portal` (31), `update_subscription` (29), `portfolio_create` (28) y `executive_portfolio_page` (27).

## Cierre de alcance V1.8

La secuencia funcional planificada quedó completada. El único trabajo restante de V1.8 es la **certificación integral final**, persistencia del acta técnica, eliminación del workflow temporal de certificación y CI canónico sobre el SHA final limpio.

## Reglas de materialización

Cada corte debe pasar, en este orden:

1. contratos dirigidos del dominio;
2. regresión completa;
3. `python scripts/audit_architecture.py --enforce`;
4. `python scripts/run_test_tier.py smoke --durations 10 --timeout 300`;
5. Alembic cuando sea relevante;
6. commit solo si todo está verde;
7. eliminación del workflow temporal;
8. CI canónico sobre el `head` limpio.

No se fusiona a V1.7 ni a `main` durante el desarrollo. El PR V1.8 permanecerá draft hasta certificación y decisión explícita de promoción.
