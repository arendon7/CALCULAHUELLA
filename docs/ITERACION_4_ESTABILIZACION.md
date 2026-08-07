# Iteración 4 · estabilización integral

## Objetivo

Validar el flujo transversal antes de añadir nuevas capacidades. Esta iteración
corrige regresiones de sincronización, reduce notificaciones redundantes y deja
una compuerta de CI reproducible para migraciones, aislamiento y regresión
integral.

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
- `app.css` es un punto de entrada que importa la hoja canónica y el overlay
  V1.4; accesibilidad y formularios se validan sobre el CSS efectivo.
- El esquema físico contiene 124 tablas: las 120 históricas más cuatro tablas
  transversales de workflow.
- El ciclo guiado conserva ocho etapas canónicas.
- El paquete macOS valida `restore_mac.sh`, que sustituyó el wrapper histórico
  de ensayo de restauración.
- La ausencia de evidencia formal del release actual mantiene cerrada la puerta
  de despliegue controlado. No se infiere evidencia desde Markdown ni desde
  `RELEASE_CANONICA.json`.

## Evidencia CI ejecutada

Commit validado: `1e621a815079085408562e57122d29f8de3b07ad`.

GitHub Actions terminó correctamente en dos workflows:

- `Validación canónica` · run 437 · `success`.
- `Iteración 4 · estabilización integral` · run 52 · `success`.

La compuerta ampliada aprobó:

1. Instalación reproducible de dependencias.
2. Verificación de árbol canónico limpio.
3. Compilación Python sin contaminar el árbol.
4. Pruebas dirigidas de Iteraciones 1–4: 28/28.
5. Alembic desde base vacía hasta `head`.
6. Alembic incremental desde `20260805_0036` hasta `head`.
7. Suite smoke.
8. Suite integral aislada: 78 bloques, 444 pruebas aprobadas.
9. Artefacto de evidencia publicado por GitHub Actions.

La suite integral conserva 11 aserciones históricas como deseleccionadas porque
fueron sustituidas por regresiones canónicas explícitas; no se eliminó la
cobertura funcional correspondiente.

Artefacto CI verde:

- ID: `9006564878`.
- Digest: `sha256:7e962895e12b513ea8ce3c2d2f77ba629dfd1db679e56c3872ab9d3b6f445aff`.

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

El PR permanece en borrador. Antes de autorizar su fusión o un release se
mantienen pendientes, como mínimo:

- revisión visual y accesibilidad en navegador real;
- Safari, Chrome y Edge;
- validación en dispositivos físicos;
- piloto controlado con usuarios reales;
- reconstrucción o generación controlada de la evidencia formal de release,
  cuando proceda y sin reutilizar certificaciones que no correspondan al árbol
  actual.
