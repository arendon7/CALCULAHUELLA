# UAT autenticada · Render staging · 2026-08-13

## Alcance

Entorno exclusivamente UAT/staging:

- host: `https://calcula-tu-huella-arendon7-preview.onrender.com`;
- base: PostgreSQL 17 aislado de Render;
- no utiliza Supabase real para las mutaciones de UAT;
- datos demostrativos/sintéticos;
- no autoriza promoción a producción ni merge del PR.

## Certificación autenticada

Workflow one-shot: `31676245921` · **SUCCESS**.

Artifact: `authenticated-render-uat-evidence` · ID `9171648728` · SHA-256 `0a905c132a8e06dca6ca395c63834f87513b6e2030addc56b11e04b703a72a23`.

Se verificaron sesiones reales para los cinco roles demo:

- Administrador → `/dashboard` + API autenticada 200;
- Consultor → `/dashboard` + API autenticada 200;
- Cliente → `/dashboard` + API autenticada 200;
- Revisor → `/dashboard` + API autenticada 200;
- Verificador → `/verificacion` + API autenticada 200.

## Persistencia y relevo entre actores

Caso sintético controlado:

- ruta: `/soporte/13`;
- asunto: `UAT online persistencia 1786604659`;
- creado por `cliente@calculatuhuella.local`;
- recuperado y respondido desde una sesión nueva por `consultor@calculatuhuella.local`;
- recuperado nuevamente desde otra sesión limpia por `cliente@calculatuhuella.local`;
- cerrado desde una nueva sesión de Consultor;
- estado final: `Cerrado`;
- resolución: `UAT online completada: persistencia entre sesiones y relevo cliente-consultor verificados.`

La prueba utilizó cuatro sesiones nuevas y confirmó persistencia en PostgreSQL Render entre sesiones y relevo Cliente → Consultor → Cliente.

## Gate pendiente derivado

Este documento se incorpora al branch para provocar un nuevo ciclo de checks y un redeploy de Render sin modificar lógica de aplicación. Después del redeploy debe comprobarse desde una sesión nueva que `/soporte/13` y su resolución continúan presentes. Ese resultado cerrará el gate de persistencia a través de restart/deploy.
