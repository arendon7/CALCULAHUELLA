# V1.7.0 · Acta de certificación integral

## Resultado

**CERTIFICADO TÉCNICAMENTE.** La consolidación V1.7 completó sus cortes planificados sin modificar la rama `main` ni promover la rama certificada.

## Identidad de la ejecución

- Rama: `refactor/v1-7-0-domain-surfaces`
- PR: `#20`
- Baseline V1.6: `092122afec70bb32f825d087b89a0401249f438a`
- SHA de entrada a certificación: `5e620d90fd646ba21e4ebbdc6a88449c2ae600c0`
- GitHub Actions run: `31406883511`

## Gates ejecutados en esta certificación

- estructura canónica: PASS;
- higiene de workflows: PASS;
- unicidad de método + ruta: PASS;
- regresión completa: **539 passed, 1 skipped**;
- barrera de deuda arquitectónica: PASS;
- smoke canónico: **56 passed, 484 deselected**;
- Alembic desde instancia vacía: PASS.

## Snapshot arquitectónico

- archivos Python: **138**;
- líneas Python: **39755**;
- rutas HTTP: **344**;
- tablas ORM: **124**;
- `app/main.py`: **2224 líneas / 81 rutas**;
- `app/database.py`: 269 líneas.

## Alcance V1.7 certificado

1. Supply Chain / Scope 3 HTTP.
2. Support HTTP.
3. Commercial Proposal HTTP.
4. Proposal Acceptance / Payments HTTP.
5. Commercial Operations HTTP.
6. Customer Success HTTP.
7. SaaS Administration HTTP.

La lógica de negocio existente permanece en sus autoridades de dominio. No se cambiaron factores, GWP, fórmulas de huella, motor de cálculo ni semántica de reporting.

## Deuda residual deliberadamente diferida

V1.7 cierra con `app/main.py` todavía como composition root parcial. Impact Intelligence, Climate Risk/Disclosure, consolidación/release governance y otras superficies transversales se difieren a un ciclo apilado posterior para evitar ampliar artificialmente el alcance certificado.

## Paso de higiene posterior

Después de esta acta debe eliminarse `certify-v17-final.yml` y ejecutarse el CI canónico una última vez sobre el SHA limpio. La certificación no autoriza por sí sola fusión a `main`; el PR permanece draft hasta una decisión explícita de promoción.
