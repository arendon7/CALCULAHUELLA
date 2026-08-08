# Iteración 4 · estabilización integral

## Objetivo

Validar el flujo transversal antes de añadir nuevas capacidades. Esta iteración
corrige regresiones de sincronización, reduce notificaciones redundantes y deja
una compuerta de CI reproducible para migraciones, aislamiento, regresión
integral y validación de la experiencia principal en motores de navegador.

## Correcciones de dominio

Los módulos especializados utilizan estados más simples que `WorkItem`. La
sincronización anterior podía mover una tarea hacia atrás, por ejemplo:

- Aceptada por revisor → En revisión.
- Cerrada → Aceptada por revisor.
- Aceptada por revisor → En implementación.

La política conserva el estado canónico más avanzado. Los registros de origen
siguen siendo autoritativos cuando expresan una devolución, bloqueo,
cancelación, cierre o reapertura.

## Notificaciones

- El actor de una transición no recibe una notificación sobre su propia acción.
- Una asignación directa no se convierte después en un aviso masivo por rol.
- Los avisos por rol excluyen al usuario que ejecutó la transición.
- Los destinatarios se deduplican por usuario y transición.

## Reconciliación histórica

La regresión completa identificó contratos de pruebas anteriores que ya no
representaban el producto canónico. Se conservaron los módulos históricos y se
reemplazaron únicamente las aserciones superadas por controles equivalentes del
contrato vigente:

- `Mi trabajo` es la primera entrada de la navegación esencial; `Centro de trabajo`
  permanece en la navegación completa.
- La landing pública utiliza el contrato V1.4 y no reintroduce slogans, precios
  o claims retirados.
- `app.css` es un punto de entrada que importa la hoja canónica, el overlay
  V1.4 y el CSS específico de `Mi trabajo`; accesibilidad y formularios se
  validan sobre el CSS efectivo.
- El esquema físico contiene 124 tablas: las 120 históricas más cuatro tablas
  transversales de workflow.
- El ciclo guiado conserva ocho etapas canónicas.
- El paquete macOS valida `restore_mac.sh`, que sustituyó el wrapper histórico
  de ensayo de restauración.
- La ausencia de evidencia formal del release actual mantiene cerrada la puerta
  de despliegue controlado. No se infiere evidencia desde Markdown ni desde
  `RELEASE_CANONICA.json`.

## Estabilización visual y CSP

La validación en navegador real detectó dos defectos que las pruebas estáticas no
podían observar:

1. `Mi trabajo` contenía CSS inline incompatible con la política CSP y su grid
   podía desbordar horizontalmente en escritorio ancho.
2. WebKit reporta un comportamiento específico al aplicar mediante JavaScript
   el ancho de la barra de progreso del tour bajo la combinación CSP3 utilizada.

Las correcciones mantienen la política de scripts cerrada y evitan ocultar el
desbordamiento con `overflow-x:hidden`:

- el CSS de `Mi trabajo` está externalizado en `app/static/css/work-items.css`;
- los hijos del grid pueden encoger mediante `min-width: 0`, los controles se
  limitan al ancho disponible y el texto largo puede partirse sin empujar el
  documento;
- la CSP diferencia estilos por elemento y por atributo, manteniendo
  `script-src 'self'`;
- el progreso del tour tiene un fallback CSS basado en el paso visible mediante
  `:has()`, por lo que WebKit conserva el 25/50/75/100 % aunque bloquee la
  escritura dinámica de `style.width`;
- los avisos conocidos de WebKit quedan registrados como evidencia separada y
  cualquier otro error de consola o de página continúa haciendo fallar la
  compuerta.

## Evidencia CI ejecutada

Commit funcional validado: `550fe51800d537ac912cf63969df0c343c82642c`.

GitHub Actions terminó correctamente en dos workflows sobre ese mismo commit:

- `Validación canónica` · run 455 · ID `31225504417` · `success`.
- `Iteración 4 · estabilización integral` · run 86 · ID `31225504191` · `success`.

La compuerta backend aprobó:

1. Instalación reproducible de dependencias.
2. Verificación de árbol canónico limpio.
3. Compilación Python sin contaminar el árbol.
4. Pruebas dirigidas de Iteraciones 1–4: 28/28.
5. Alembic desde base vacía hasta `head`.
6. Alembic incremental desde `20260805_0036` hasta `head`.
7. Suite smoke.
8. Suite integral aislada: 78/78 bloques, 444 pruebas aprobadas, 0 fallos y 0 errores.
9. Artefactos de evidencia publicados por GitHub Actions.

La suite integral conserva 11 aserciones históricas como deseleccionadas porque
fueron sustituidas por regresiones canónicas explícitas; no se eliminó la
cobertura funcional correspondiente.

Artefacto backend:

- `iteration4-stabilization-evidence` · ID `9012125020`.
- Digest: `sha256:afe0c8ab26cb5e8b41ab14a3f50cff670cc0f39ed54b97fd2af9efd2e5ea7373`.

## Evidencia de navegador

La compuerta ejecutó `/mi-trabajo?scope=all` con login demo y base aislada en
motores Playwright Chromium, Firefox y WebKit. Cada motor validó 1440×900,
1024×768, 390×844 y 360×800, además de encabezado, `aria-current`, nombres
accesibles, foco por teclado, errores de página, errores de consola y overflow
horizontal.

### Chromium

- Job: `Mi trabajo · chromium` · `success`.
- Overflow: 0 px en los cuatro viewports.
- Errores de consola: 0.
- Errores de página: 0.
- Progreso inicial del tour: 25 %.
- Artefacto `browser-gate-chromium` · ID `9011958815`.
- Digest: `sha256:a6a6e9f71ede278da0af0e426a7eea1f4d5d74b8d2c82a4dca630e515bda05f7`.

### Firefox

- Job: `Mi trabajo · firefox` · `success`.
- Overflow: 0 px en los cuatro viewports.
- Errores de consola: 0.
- Errores de página: 0.
- Progreso inicial del tour: 25 %.
- Artefacto `browser-gate-firefox` · ID `9011962214`.
- Digest: `sha256:a90b58cd9e02cc0368f67bee17020cfe3df30c7c92ba9fc0d19cd18d06b5c627`.

### WebKit

- Job: `Mi trabajo · webkit` · `success`.
- Overflow: 0 px en los cuatro viewports.
- Errores reales de consola: 0.
- Errores de página: 0.
- Progreso inicial del tour mediante fallback CSS: 25 %.
- Avisos conocidos del motor registrados: 4, todos correspondientes al intento
  de `style.width` que WebKit rechaza bajo su interpretación de CSP; no se
  clasifican como errores funcionales y permanecen visibles en el JSON de
  evidencia.
- Artefacto `browser-gate-webkit` · ID `9011970287`.
- Digest: `sha256:dff02d38bad35faf5814a0b048c320c1f33ba881451d9b3331b5e15f31955112`.

Esta evidencia corresponde a motores Playwright en GitHub Actions Linux. No debe
presentarse como validación de Safari, Microsoft Edge o Google Chrome físicos.

## Gobierno de liberación

Que CI esté verde no autoriza por sí solo un release controlado ni producción
pública. En el árbol actual no existe `release/FINAL_TEST_EVIDENCE.json` ni se
encuentra completo el bundle formal histórico de aprobaciones internas. Por
ello:

- `controlled_release_ready = false` continúa siendo el resultado correcto.
- `production_ready = false` continúa siendo obligatorio.
- No se debe inferir una aprobación formal desde evidencia histórica o
  documentación declarativa.

## Compuertas pendientes

El PR permanece en borrador. La validación automatizada de backend y motores de
navegador ya no es una compuerta pendiente. Antes de autorizar su fusión o un
release se mantienen pendientes, como mínimo:

- prueba en Google Chrome, Microsoft Edge y Safari de distribución cuando se
  requiera validar los navegadores comerciales y no solo sus motores;
- validación en dispositivos físicos relevantes;
- piloto controlado con usuarios reales y observación de tareas completas;
- reconstrucción o generación controlada de la evidencia formal de release,
  cuando proceda y sin reutilizar certificaciones que no correspondan al árbol
  actual.
