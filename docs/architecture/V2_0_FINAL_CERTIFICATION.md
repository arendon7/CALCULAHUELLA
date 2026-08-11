# V2.0 · Certificación final de product readiness

## Estado

**CERTIFICADA** para cierre técnico sobre la rama `stabilization/v2-0-0-product-readiness`.

Esta acta se generó únicamente después de superar de nuevo los gates integrales y de verificar criptográficamente el artefacto Mac correspondiente al mismo SHA de producto. El conteo de Pytest se reconcilió contra la salida textual del propio run integral porque el primer parser del XML JUnit leyó el nodo contenedor y reportó 0/0 pese a que la suite había finalizado correctamente.

## Baseline y gobierno

- Baseline V1.9 certificada: `19d46ba63dfc243d69c7aa42f94e58d4576435d0`.
- SHA de producto V2.0 certificado: `cef1168d8d8744600a660c90160a95bd442f10fd`.
- PR: **#23**, permanece **draft**.
- `main` permanece fuera de alcance; esta certificación **no autoriza merge automático**.

## Evidencia integral

- Certificación integral independiente: **run 31504512772 · success**.
- Pytest integral directo: **640 passed / 1 skipped** en 62,79 s. El único skip corresponde a `tests/test_v044_demo_environment.py::test...` marcado como prueba exclusiva del paquete macOS.
- Product-readiness completo: **run 31501902412 · success**, con 8 jobs: regresión/seguridad/continuidad, PostgreSQL restore, Chromium, Firefox, WebKit, cinco roles, handoff y huella climática completa.
- CI canónico del SHA de producto: **run 31501902400 · success**.
- Arquitectura: **green**.
- Smoke independiente: **56 passed**.
- Alembic desde instancia vacía hasta `20260810_0039`: **green**.
- Estructura canónica comprobada sobre copia sin `.git`: **green**.
- Contratos HTTP: **344 únicos**, sin duplicados `(method, path)`.
- Tablas ORM: **124**.
- Python de aplicación: **157 archivos / 40.293 líneas**.
- `app/main.py`: **639 líneas / 3 rutas directas**.

## Artefacto Mac reproducible

- Workflow de empaquetado: **run 31501895998 · success**.
- Artifact ID: **9105414995**.
- Nombre: `Calcula-Tu-Huella-Mac-cef1168d8d8744600a660c90160a95bd442f10fd`.
- Tamaño del ZIP de Actions: **135.918.224 bytes**.
- SHA-256 del ZIP de Actions: `da739408a9f23c5601602fe0361db462c7ee421a722702eb9692b3513f025fc9`.
- SHA-256 del ZIP entregable interno: `6368dbd77f3286196e7167b554322b7ade8b9bf44784ae77b19542d94d7755dd`.
- Entradas verificadas contra `MANIFEST_SHA256.txt`: **4.005**, sin discrepancias.
- Runtime: **CPython 3.12.13 / 20260807**.
- El runtime del paquete declara exactamente el SHA de producto certificado.
- El runtime excluye `tests/`, `.github/` y `packaging/` de la carga distribuida.

## Capacidades de promotion-readiness cerradas en V2.0

1. Gate moderno de product readiness asociado al PR actual.
2. Continuidad PostgreSQL con backup, restore aislado y auditoría.
3. Paquete Mac reproducible, hash-locked y con procedencia explícita.
4. Journey climático completo en navegador real: captura operativa, cadena de proveedores, cálculo, revisión, segregación de aprobación, informe, cierre y paquete de verificación.
5. Frontera correcta entre captura de actividad y fuente consolidada de proveedores, con progreso agregado coherente.
6. Portal de proveedores protegido por CSRF sin romper el flujo público seguro.
7. Liveness/readiness separados: el servidor abre puerto sin bloquearse por Storage externo; `/api/ready` conserva diagnóstico estricto.
8. Timeouts y reintentos S3 acotados; configuración inválida falla antes de tocar red.

## Composition root

Se preserva la frontera V1.9. Las únicas rutas HTTP directas en `app/main.py` son:

- `GET /api/health`
- `GET /api/ready`
- `GET /modulos`

## Higiene de workflows

Tras persistir esta acta y retirar el certificador temporal, el árbol vuelve exactamente a los cuatro workflows permanentes:

- `.github/workflows/ci.yml`
- `.github/workflows/iteration4-stabilization.yml`
- `.github/workflows/package-mac-selfcontained.yml`
- `.github/workflows/pages.yml`

No permanecen workflows `materialize-*`, `diagnose-*` ni certificadores temporales.

## Alcance de la afirmación

Esta certificación demuestra **readiness técnico y operativo controlado del ciclo V2.0**. No convierte por sí sola una demo o configuración sin servicios externos reales en producción pública certificada, ni sustituye verificación independiente de inventarios de carbono.

El cierre de gobierno exige únicamente CI canónico verde sobre el SHA documental limpio y actualizar PR #23 manteniéndolo draft. No se autoriza promoción a `main` mediante esta acta.
