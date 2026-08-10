# V1.8.0 · Acta de certificación integral

## Resultado

**CERTIFICADO TÉCNICAMENTE.** La consolidación V1.8 completó sus superficies estratégicas planificadas sin modificar `main` ni promover la rama certificada.

## Identidad de la ejecución

- Rama: `refactor/v1-8-0-strategic-surfaces`
- PR: `#21`
- Baseline V1.7: `d015f21af67bc834d72b1dd6cd97d6082efe04c5`
- SHA de entrada a certificación: `be87ee5ed9f1dc36ba1909aa20cb9dcbd67b88ac`
- GitHub Actions run: `31409201393`

## Gates ejecutados en esta certificación

- estructura canónica: PASS;
- higiene de workflows: PASS;
- unicidad de método + ruta: PASS;
- regresión completa: **551 passed, 1 skipped**;
- barrera de deuda arquitectónica: PASS;
- smoke canónico: **56 passed, 496 deselected**;
- Alembic desde instancia vacía: PASS.

## Snapshot arquitectónico

- archivos Python: **142**;
- líneas Python: **39867**;
- rutas HTTP: **344**;
- tablas ORM: **124**;
- `app/main.py`: **1583 líneas / 49 rutas**;
- `app/database.py`: **269 líneas**.

## Alcance V1.8 certificado

1. Impact Intelligence HTTP.
2. Climate Risk HTTP.
3. Climate Disclosure HTTP.
4. Consolidation / Release Governance HTTP.

Las autoridades de negocio existentes permanecen en `impact_intelligence.py`, `climate_risk.py`, `climate_disclosure.py`, `consolidation.py` y `architecture.py`. No se cambiaron factores, GWP, fórmulas de huella, motor de cálculo ni semántica de reporting.

## Deuda residual deliberadamente diferida

Dashboard/analítica, escenarios, verificación, automatizaciones, cuenta de servicio/suscripción, onboarding, configuración de plataforma, control documental y otras superficies transversales se difieren a un ciclo apilado V1.9 para evitar ampliar artificialmente el alcance certificado.

## Paso de higiene posterior

Después de esta acta debe eliminarse `certify-v18-final.yml` y ejecutarse el CI canónico una última vez sobre el SHA limpio. La certificación no autoriza por sí sola fusión a V1.7 ni a `main`; el PR permanece draft hasta una decisión explícita de promoción.
