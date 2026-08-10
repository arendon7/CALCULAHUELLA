# V1.8.0 · Consolidación de superficies estratégicas

## Baseline

V1.8 parte exactamente del cierre limpio y certificado de V1.7 en `d015f21af67bc834d72b1dd6cd97d6082efe04c5`.

La rama `refactor/v1-7-0-domain-surfaces` queda congelada como baseline certificada. `main` continúa fuera de alcance.

## Objetivo

Reducir la deuda residual de `app/main.py` en bounded contexts estratégicos que ya cuentan con lógica de dominio separada, moviendo únicamente sus superficies HTTP y helpers cohesionados.

No se reescriben modelos climáticos, fórmulas de impacto, factores, GWP, motor de cálculo, semántica de reporting ni reglas de negocio salvo que un corte posterior lo declare de manera explícita y tenga contratos propios.

## Secuencia inicial

1. **Impact Intelligence HTTP** — mantener `app/impact_intelligence.py` como autoridad de métricas, snapshots, benchmarks y comparación de portafolio.
2. **Climate Risk HTTP** — mantener `app/climate_risk.py` como autoridad de evaluación, scoring, controles y estados.
3. **Climate Disclosure HTTP** — mantener `app/climate_disclosure.py` como autoridad de escenarios, divulgación y briefing de junta.
4. **Consolidation / Release Governance HTTP** — separar hallazgos, gates de release y validaciones de journey sin cambiar decisiones de gobierno.
5. Inventario residual y certificación integral V1.8.

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
