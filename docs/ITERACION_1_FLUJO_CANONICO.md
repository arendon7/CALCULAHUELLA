# Iteración 1 · Flujo canónico de trabajo

## Estado del documento

- Rama: `integration/workflow-v1.5.0`
- Base: `integration/uiux-v1.4.0`
- Naturaleza: diseño de dominio y persistencia aditiva
- Impacto sobre producción: ninguno hasta integrar rutas y migraciones
- Principio rector: introducir una unidad universal de trabajo sin retirar todavía los registros especializados existentes

## 1. Problema que resuelve

La plataforma ya dispone de solicitudes, datos, evidencias, hallazgos, observaciones, cierres mensuales, revisiones, aprobaciones, informes, acciones de reducción y soporte. Sin embargo, cada módulo administra su propio estado y no existe una bandeja transversal que responda de forma consistente:

1. ¿Qué debe hacerse?
2. ¿Quién debe hacerlo?
3. ¿Cuándo vence?
4. ¿Qué criterio determina que la entrega es suficiente?
5. ¿Qué bloquea la tarea?
6. ¿Quién debe actuar después?
7. ¿Qué registro, evidencia o decisión originó el trabajo?
8. ¿Cuál es su trazabilidad completa?

La Iteración 1 crea el contrato de dominio que permitirá responder esas preguntas sin simplificar o eliminar las capacidades técnicas existentes.

## 2. Proceso canónico de ocho etapas

| Nº | Código | Nombre | Resultado de salida |
|---:|---|---|---|
| 1 | `diagnose` | Diagnosticar | Diagnóstico trazable y ruta de implementación acordada |
| 2 | `configure` | Configurar | Inventario, límites, responsables y metodología preparados |
| 3 | `collect` | Recopilar | Datos y evidencias entregados o excepción documentada |
| 4 | `validate_close` | Validar y cerrar periodos | Periodo validado, cerrado o devuelto con hallazgos accionables |
| 5 | `calculate` | Calcular | Resultados reproducibles con insumos metodológicos identificados |
| 6 | `review_approve` | Revisar y aprobar | Decisión de aprobación o devolución con responsable y plazo |
| 7 | `report_publish` | Reportar y controlar publicación | Artefacto versionado y vinculado con su autorización de uso |
| 8 | `reduce_continue` | Reducir y continuar | Acciones asignadas y siguiente ciclo preparado |

### Regla de arquitectura de información

Las etapas no sustituyen los espacios principales de navegación. La navegación agrupa capacidades; las etapas explican el ciclo de vida.

Espacios principales previstos:

- Mi trabajo.
- Información.
- Cálculo y calidad.
- Informes.
- Reducción.
- Colaboración.

## 3. Unidad universal: `WorkItem`

Un `WorkItem` representa una obligación concreta, asignable, verificable y trazable. No es una nota genérica ni un mensaje de soporte.

### 3.1 Campos esenciales

- Organización e inventario relacionado.
- Etapa canónica.
- Tipo de trabajo.
- Título y descripción.
- Estado.
- Prioridad.
- Solicitante.
- Responsable por usuario, correo, rol o área.
- Fecha de vencimiento.
- Criterios de aceptación.
- Próxima acción.
- Motivo de bloqueo.
- Entidad y ruta de origen.
- Fechas de aceptación, entrega, revisión, aprobación y cierre.
- Versión para control de concurrencia.

### 3.2 Registros asociados

- `WorkItemEvent`: historial inmutable de transiciones y decisiones.
- `WorkItemLink`: relación con dato, evidencia, fuente, cierre, informe, hallazgo u otra entidad.
- `WorkItemDependency`: dependencias entre tareas.

## 4. Tipos de trabajo iniciales

| Código | Etiqueta | Etapa predeterminada |
|---|---|---|
| `data_request` | Solicitud de dato | Recopilar |
| `evidence_request` | Solicitud de evidencia | Recopilar |
| `data_correction` | Corrección de dato | Validar y cerrar periodos |
| `quality_finding` | Hallazgo de calidad | Validar y cerrar periodos |
| `monthly_close` | Cierre mensual | Validar y cerrar periodos |
| `factor_review` | Revisión de factor | Calcular |
| `inventory_review` | Revisión de inventario | Revisar y aprobar |
| `report_approval` | Aprobación de informe | Reportar y controlar publicación |
| `reduction_action` | Acción de reducción | Reducir y continuar |
| `support_follow_up` | Seguimiento de soporte | Recopilar |
| `integration_exception` | Excepción de integración | Recopilar |
| `next_period_setup` | Preparación del siguiente periodo | Reducir y continuar |

## 5. Estados canónicos

Los estados distinguen la aceptación de la asignación de la aceptación técnica de la entrega.

| Código | Etiqueta | Significado |
|---|---|---|
| `draft` | Borrador | Todavía no existe asignación |
| `assigned` | Asignada | Existe responsable |
| `accepted_by_assignee` | Aceptada por responsable | El responsable confirmó atención |
| `in_progress` | En preparación | La entrega está siendo preparada |
| `blocked` | Bloqueada | Existe impedimento documentado |
| `submitted` | Entregada | El resultado fue enviado a control |
| `validating` | En validación | Se revisan integridad y criterios formales |
| `under_review` | En revisión | Se evalúa suficiencia técnica o metodológica |
| `accepted_by_reviewer` | Aceptada por revisor | La entrega fue aceptada |
| `returned` | Devuelta | Requiere correcciones concretas |
| `closed` | Cerrada | Terminó con decisión y trazabilidad completas |
| `cancelled` | Cancelada | Dejó de ser aplicable con motivo documentado |

## 6. Transiciones permitidas

```text
Borrador
  └─ asignar → Asignada

Asignada
  └─ aceptar asignación → Aceptada por responsable

Aceptada por responsable
  └─ iniciar → En preparación

En preparación
  ├─ bloquear → Bloqueada
  └─ entregar → Entregada

Bloqueada
  └─ reanudar → En preparación

Entregada
  ├─ iniciar validación → En validación
  └─ devolver → Devuelta

En validación
  ├─ enviar a revisión → En revisión
  └─ devolver → Devuelta

En revisión
  ├─ aceptar entrega → Aceptada por revisor
  └─ devolver → Devuelta

Aceptada por revisor
  ├─ cerrar → Cerrada
  └─ devolver → Devuelta

Devuelta
  └─ reiniciar corrección → En preparación

Cerrada
  └─ reabrir con autorización y motivo → Devuelta
```

La cancelación está disponible antes del cierre, pero siempre exige una razón documentada.

## 7. Reglas obligatorias

### Asignación

Una tarea no puede pasar de Borrador a Asignada sin:

- persona, área o rol responsable; y
- criterio de aceptación verificable.

### Bloqueo

Bloquear exige indicar el impedimento. El bloqueo no equivale a cierre ni a cancelación.

### Devolución

Toda devolución exige una razón concreta. En la implementación de interfaz deberá incluir:

- qué falta;
- qué debe corregirse;
- responsable;
- plazo; y
- enlace directo al objeto afectado.

### Cierre

Solo una entrega aceptada por el revisor puede cerrarse. El cierre debe producir un evento trazable.

### Reapertura

La reapertura requiere capacidad de aprobación y un motivo. La tarea vuelve a Devuelta, nunca a Borrador.

## 8. Segregación de funciones

| Rol | Capacidades del flujo |
|---|---|
| Administrador | Crear, asignar, ejecutar, validar, revisar, aprobar y auditar |
| Consultor | Crear, asignar, ejecutar, validar y revisar |
| Cliente | Aceptar, preparar, bloquear, reanudar, entregar y corregir trabajo asignado |
| Revisor | Validar, revisar, aprobar, cerrar y reabrir |
| Verificador | Consultar trazabilidad; no altera el trabajo |

La interfaz futura ocultará acciones no autorizadas, pero la autorización seguirá verificándose en el servidor.

## 9. Estrategia de migración progresiva

### Fase A · coexistencia

- Crear tablas de trabajo.
- Mantener `DataRequest`, `ReviewObservation`, `PeriodClose`, `DataQualityFinding`, `SupportTicket` y demás registros existentes.
- No alterar rutas ni plantillas.

### Fase B · adaptadores

Crear adaptadores idempotentes:

- `DataRequest` → `WorkItem(data_request)`.
- `ReviewObservation` → `WorkItem(data_correction)`.
- `DataQualityFinding` → `WorkItem(quality_finding)`.
- `PeriodClose` → `WorkItem(monthly_close)`.
- `ReportArtifact` pendiente de aprobación → `WorkItem(report_approval)`.
- `ReductionAction` → `WorkItem(reduction_action)`.

Cada adaptador debe guardar un `WorkItemLink` hacia la entidad original y evitar duplicados.

### Fase C · Mi trabajo

- Bandeja transversal.
- Vistas: asignadas a mí, solicitadas por mí, devueltas, vencidas, bloqueadas, en validación, en revisión y pendientes de aprobación.
- Acciones contextuales que redirijan al módulo especializado.

### Fase D · automatización de transiciones

Las acciones sobre los registros especializados actualizarán el `WorkItem` asociado. Se retirarán los cambios manuales de estado cuando exista una acción de dominio equivalente.

### Fase E · consolidación

Solo después de pruebas y pilotos se evaluará retirar campos o flujos duplicados. No se eliminará información histórica.

## 10. No objetivos de esta iteración

- No se crea todavía la pantalla Mi trabajo.
- No se sustituyen solicitudes ni observaciones existentes.
- No se cambia la navegación.
- No se altera la landing.
- No se ejecutan migraciones sobre la rama estable.
- No se habilitan notificaciones o automatizaciones nuevas.

## 11. Criterios de aceptación de la Iteración 1

1. Existen exactamente ocho etapas canónicas.
2. Todos los tipos de trabajo tienen una etapa predeterminada válida.
3. Todos los estados y destinos de transición existen.
4. Toda acción tiene una política de capacidad.
5. Asignar exige responsable y criterio de aceptación.
6. Bloquear, devolver, cancelar y reabrir exigen motivo.
7. Los roles actuales tienen una política explícita.
8. Las tablas son aditivas y referencian organización, inventario y usuarios existentes.
9. La migración depende de `20260805_0036`.
10. La versión estable no fue modificada.

## 12. Siguiente corte técnico

La Iteración 2 implementará:

- servicio de aplicación para crear y transicionar tareas;
- eventos de auditoría;
- adaptador inicial para `DataRequest`;
- consultas de bandeja;
- ruta `/mi-trabajo`;
- pruebas de autorización, aislamiento por organización y vencimientos.
