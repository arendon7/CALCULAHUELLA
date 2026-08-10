# V2.0.0 · Product readiness y estabilidad operativa

## Baseline

V2.0 parte exactamente del cierre limpio y certificado de V1.9 en `19d46ba63dfc243d69c7aa42f94e58d4576435d0`.

La rama V1.9 `refactor/v1-9-0-core-surfaces` queda congelada como baseline certificada. `main` permanece fuera de alcance y no se autoriza promoción automática.

Baseline técnica heredada:

- suite integral V1.9: **598 passed / 1 skipped**;
- smoke: **56 passed**;
- contratos HTTP: **344 únicos**;
- tablas ORM: **124**;
- `app/main.py`: **639 líneas / 3 rutas directas**;
- CI canónico final V1.9: `31429416721 = success`.

## Cambio de objetivo

V2.0 no continúa el refactor masivo de `app/main.py`. El composition root ya alcanzó una frontera razonable.

El objetivo de este ciclo es convertir las capacidades existentes de producto, seguridad, continuidad y entrega en una **barrera de promoción actual, reproducible y observable**. Un cambio no debe considerarse listo solo porque compila o pasa smoke: debe demostrar que los recorridos críticos siguen funcionando, que una copia de seguridad es recuperable, que los controles de seguridad no retroceden y que los artefactos de distribución pueden identificarse y verificarse.

## Hallazgos de baseline que justifican V2.0

### 1. Gates de estabilización desacoplados de las ramas actuales

`.github/workflows/iteration4-stabilization.yml` contiene una batería valiosa:

- workflow canónico y roles;
- sincronización de `WorkItem` con fuentes especializadas;
- aislamiento multiempresa;
- accesibilidad y CSP;
- Playwright en Chromium, Firefox y WebKit;
- cinco recorridos por rol;
- relevo completo entre actores;
- migración desde vacío e incremental;
- smoke y suite integral.

Sin embargo, sus triggers todavía apuntan a `integration/workflow-v1.5.0` e `integration/uiux-v1.4.0`. Por tanto, esa batería no actúa como gate automático de los PR modernos V1.9/V2.0.

### 2. El CI canónico actual es necesario pero no suficiente como release gate

`.github/workflows/ci.yml` protege cualquier PR con:

- estructura canónica;
- deuda arquitectónica;
- smoke;
- Alembic desde vacío.

No ejecuta los browser journeys, el relevo multirol, la regresión integral ni los drills operativos como requisito de promoción.

### 3. Continuidad y seguridad ya existen y deben protegerse, no reinventarse

La base actual ya cubre:

- backup firmado HMAC-SHA256 y verificación de payloads;
- replicación offsite;
- restore drill aislado y rechazo seguro de backups corruptos;
- evidencia persistente del drill;
- throttling persistente de login;
- CSRF;
- request IDs;
- cadena de auditoría resistente a manipulación;
- validación de firmas/contenido de uploads;
- perfil productivo de siete capas.

V2.0 debe convertir estas capacidades en gates de readiness con evidencia, no cambiar su semántica salvo defecto demostrado.

### 4. Empaquetado Mac autocontenido no está alineado con la línea actual

`.github/workflows/package-mac-selfcontained.yml`:

- aún se dispara contra `integration/workflow-v1.5.0`;
- contiene narrativa histórica de “rama de integración”;
- resuelve `python-build-standalone` mediante el release `latest`, lo que reduce reproducibilidad;
- no forma hoy parte de una promoción V2.0 verificable.

El empaquetado debe evolucionar hacia un artefacto con versión, commit, checksums y procedencia explícitos, sin introducir dependencias de red en tiempo de instalación.

## Principios de gobierno V2.0

1. **No tocar fórmulas para satisfacer gates.** Factores, GWP, ecuaciones de huella, metodología y semántica contable quedan fuera de alcance salvo defecto reproducible independiente.
2. **No reabrir `main.py` por conveniencia.** Se mantiene como composition root salvo fix funcional justificado.
3. **No declarar readiness con tests unitarios solamente.** Deben existir journeys reales y evidencia operativa.
4. **No producir artefactos opacos.** Todo paquete de distribución debe identificar commit, dependencias/runtime y checksums.
5. **No confundir demo con producción pública.** La aplicación conserva el bloqueo conservador de `production_ready` cuando falte evidencia externa real.
6. **Cada corte queda limpio.** Workflow temporal de materialización/certificación se elimina antes de aceptar el `head` limpio; workflows de producto deliberadamente permanentes se documentan como tales.
7. **Sin merge automático.** La rama y su PR permanecen draft hasta promoción explícita.

## Secuencia V2.0

### Corte 1 · Release gate actual

Convertir la batería histórica de estabilización en un gate de product readiness aplicable al PR V2.0.

Debe cubrir, como mínimo:

- `tests/test_iteration15_canonical_workflow.py`;
- `tests/test_iteration16_area_assignment.py`;
- `tests/test_iteration16_work_items.py`;
- `tests/test_iteration17_integrated_workflow.py`;
- `tests/test_iteration18_stabilization.py`;
- `tests/test_iteration19_role_journeys.py`;
- `tests/test_v024_security_hardening.py`;
- `tests/test_v034_operational_hardening.py`;
- `tests/test_v057_production_readiness.py`;
- `tests/test_v100_rc1_release_candidate.py`;
- migración vacía + incremental;
- smoke + suite integral;
- Playwright Chromium/Firefox/WebKit;
- journeys de roles;
- handoff completo.

La intención es activar evidencia existente y añadir solo contratos faltantes; no crear un segundo sistema de workflow paralelo.

### Corte 2 · Continuidad y auditabilidad de release

Endurecer la barrera operacional alrededor de:

- backup firmado y verificado;
- restore drill reproducible;
- rechazo de backup corrupto sin tocar la base activa;
- resultado de continuidad visible en diagnóstico/readiness;
- ejecución de `scripts/run_production_audit.py` en un entorno aislado cuando sus precondiciones lo permitan;
- evidencia JUnit/logs/artifacts con retención acotada.

### Corte 3 · Artefacto Mac reproducible

Alinear el paquete autocontenido con V2.0:

- trigger relevante y/o ejecución manual explícita desde el SHA que se desea empaquetar;
- runtime Python resuelto de forma reproducible, evitando depender silenciosamente de `latest`;
- `MANIFEST` de build con commit, versión, arquitectura y runtime;
- SHA-256 de ZIP y componentes críticos;
- validación de wheelhouse para arm64/x86_64;
- validación sintáctica de entrypoints y lifecycle canónico;
- mantener instalación offline una vez descargado el paquete.

No se afirmará compatibilidad Mac real únicamente porque un runner Linux haya construido el ZIP; la evidencia distinguirá build-valid de host-validated.

### Corte 4 · Journey crítico de extremo a extremo

Cerrar una prueba de promoción que atraviese una cadena de negocio real, no solo pantallas aisladas. Objetivo mínimo:

1. autenticación y contexto de organización;
2. acceso por rol correcto;
3. inventario/contexto activo;
4. solicitud/carga o dato operativo;
5. creación/sincronización de trabajo;
6. revisión/relevo/aceptación;
7. resultado o artefacto de cierre disponible para el actor autorizado;
8. aislamiento multiempresa durante todo el recorrido.

Se reutilizarán `browser_workflow_gate.py`, `browser_role_gate.py`, `browser_handoff_gate.py` y los servicios existentes antes de introducir un runner adicional.

### Corte 5 · Observabilidad y fallo seguro

Verificar que una degradación operativa sea diagnóstica y limitada:

- `/api/health` para liveness;
- `/api/ready` para readiness real;
- request ID propagado;
- errores sin fuga de secretos;
- estados de almacenamiento/DB/continuidad distinguibles;
- timeouts explícitos en dependencias externas relevantes;
- evidencia útil para soporte sin convertir diagnósticos externos lentos en bloqueo indefinido del servidor.

### Cierre V2.0 · Certificación integral

Antes de cerrar el ciclo:

- estructura canónica sin `.git`;
- workflow hygiene;
- contratos HTTP sin duplicados;
- suite integral;
- arquitectura;
- smoke;
- Alembic desde vacío;
- release/product-readiness gate completo;
- continuidad/restore;
- evidencia de empaquetado;
- acta `docs/architecture/V2_0_FINAL_CERTIFICATION.md` generada solo después de todos los PASS;
- eliminación de certificadores/materializadores temporales;
- CI canónico final sobre SHA limpio.

## No alcance inicial

- promoción o merge a `main`;
- cambio de factores de emisión, GWPs o fórmulas;
- rediseño general de UI;
- nuevos módulos comerciales o climáticos;
- migración de base de datos sin necesidad funcional demostrada;
- afirmar producción pública mientras los checks externos reales continúen pendientes.

## Estado al abrir el ciclo

- rama de trabajo: `stabilization/v2-0-0-product-readiness`;
- base exacta: `19d46ba63dfc243d69c7aa42f94e58d4576435d0`;
- siguiente acción: abrir PR draft contra `refactor/v1-9-0-core-surfaces` y materializar el Corte 1 sin modificar `main` ni lógica metodológica.
