# ADR-002 · Workspace histórico con contexto explícito de inventario

**Estado:** Aceptado para implementación incremental  
**Versión objetivo:** V2.38+  
**Ámbito:** navegación, lectura histórica, permisos y trazabilidad  

## 1. Problema

Calcula tu Huella conserva múltiples inventarios por organización. La autoridad actual es deliberadamente simple y veraz:

- las rutas generales sin `inventory_id` trabajan con el periodo más reciente de la organización;
- `/inventario` es un alias hacia ese periodo por defecto;
- `/inventarios/{inventory_id}` permite consultar un expediente explícito;
- consultar un periodo histórico **no cambia** el periodo por defecto global.

Esta arquitectura evita un estado oculto de “inventario activo”, pero limita la profundidad de la consulta histórica: hoy varias superficies generales —resultados, análisis, reducción, informes y cierre— resuelven el periodo más reciente aunque el usuario venga de un expediente histórico.

La solución no será introducir una selección global persistente ni una variable de sesión ambigua. Se implementará un workspace explícitamente parametrizado por inventario.

## 2. Decisión

Se adopta un **namespace de rutas explícitas por inventario** para las superficies que necesiten consulta histórica profunda.

Forma canónica:

```text
/inventarios/{inventory_id}/...
```

Las rutas generales existentes se conservarán como experiencia operacional del periodo por defecto.

### 2.1 Principios obligatorios

1. **Sin “inventario activo” oculto.** No se guardará en sesión un inventario seleccionado para reinterpretar silenciosamente rutas generales.
2. **Periodo por defecto estable.** Las rutas generales continúan resolviendo el inventario más reciente mediante la autoridad existente.
3. **Contexto explícito en URL.** Toda consulta histórica profunda debe conservar `inventory_id` en la ruta.
4. **Misma autorización.** El namespace explícito no amplía permisos; reutiliza los controles de organización, rol y capacidad actuales.
5. **Misma metodología.** Las nuevas rutas no alteran factores, GWP, fórmulas, consolidación, gates ni semántica de publicación.
6. **Lectura antes que mutación.** La primera fase prioriza lectura histórica. Las mutaciones solo se habilitan cuando el dominio ya tenga una operación explícitamente segura para ese inventario y el inventario no esté bloqueado.
7. **Inventario cerrado = inmutable.** Un periodo cerrado nunca se vuelve editable por entrar a una ruta explícita.
8. **Sin duplicar servicios.** Los handlers general y explícito deben delegar en las mismas funciones de dominio y construcción de contexto.
9. **Trazabilidad visible.** Topbar, breadcrumb, periodo y enlaces siguientes deben mantener el mismo `inventory_id` durante una consulta explícita.
10. **Salida inequívoca.** Toda vista histórica debe ofrecer `Ver periodos` e `Ir al periodo por defecto`.

## 3. Matriz de rutas objetivo

| Superficie | Ruta general existente | Ruta explícita objetivo | Fase inicial |
|---|---|---|---|
| Expediente | `/inventario` | `/inventarios/{id}` | Existente |
| Fuentes | periodo por defecto / navegación general | `/inventarios/{id}/fuentes` | Existente |
| Datos y evidencias | `/informacion` | `/inventarios/{id}/informacion` | Lectura histórica |
| Resultados | `/calculos` | `/inventarios/{id}/calculos` | Lectura histórica |
| Análisis | `/analisis` | `/inventarios/{id}/analisis` | Lectura histórica |
| Reducción | `/reduccion` | `/inventarios/{id}/reduccion` | Lectura histórica |
| Informes | `/reportes` | `/inventarios/{id}/reportes` | Lectura histórica |
| Cierre y entrega | `/entrega-profesional` | `/inventarios/{id}/entrega-profesional` | Lectura histórica |

La existencia de una fila en esta matriz **no autoriza por sí sola** una operación de escritura histórica.

## 4. Resolución de inventario

Cada handler explícito debe resolver el inventario con las mismas garantías que el dominio ya aplica:

```python
inventory = get_inventory(session, user, inventory_id)
```

La resolución debe fallar si el inventario no pertenece a la organización activa. No se admiten IDs de otra organización, aunque el usuario conozca el identificador.

Las rutas generales mantienen:

```python
inventory = get_inventory(session, user)
```

Por tanto, la ausencia de `inventory_id` continúa significando **periodo más reciente por defecto**, no “último periodo que el usuario abrió”.

## 5. Contrato de navegación

Dentro de una ruta explícita, todo enlace que permanezca en la misma superficie funcional debe conservar el inventario.

Ejemplo:

```text
/inventarios/17/calculos
  → /inventarios/17/analisis
  → /inventarios/17/reduccion
  → /inventarios/17/reportes
```

No se permitirá que un CTA aparentemente contextual salte a `/analisis`, `/reduccion` o `/reportes` sin advertencia, porque esas rutas generales resolverían el periodo por defecto.

Los enlaces que deliberadamente abandonen el contexto histórico deben nombrarlo de forma explícita:

- `Ir al periodo por defecto`
- `Volver al flujo operativo actual`
- `Ver periodos`

## 6. Contrato visual

Toda vista explícita debe mostrar, como mínimo:

- nombre del inventario;
- rango exacto de fechas;
- estado del inventario;
- indicador `Periodo mostrado` en el shell;
- una señal de `Consulta histórica` cuando no sea el periodo por defecto;
- acceso al expediente explícito;
- acceso a la lista de periodos.

No se usará el texto “inventario activo” ni “periodo activo”.

## 7. Escritura y bloqueo

La introducción de rutas explícitas **no implica** habilitar POSTs parametrizados de inmediato.

Antes de permitir una mutación desde una vista explícita deben cumplirse los siguientes criterios:

1. el endpoint recibe o deriva un `inventory_id` inequívoco;
2. el recurso objetivo pertenece a ese inventario;
3. el inventario pertenece a la organización activa;
4. el rol posee la capacidad existente;
5. el inventario no está bloqueado cuando la operación sea mutable;
6. el redirect posterior conserva el contexto explícito;
7. existe un test de no-fuga hacia el periodo por defecto.

Si alguno de estos contratos no existe, la vista histórica será de solo lectura y deberá indicarlo.

## 8. Publicación y documentos

Un periodo histórico puede tener artefactos, aprobación y nivel de publicación distintos del periodo por defecto. Por tanto:

- `delivery_readiness` siempre debe calcularse sobre el inventario explícito;
- el historial documental se filtra por ese inventario;
- descargar un artefacto existente conserva su identidad y SHA-256;
- generar una nueva versión desde un periodo cerrado queda sometido a las reglas de bloqueo existentes;
- `Revisado y aprobado` continúa siendo distinto de `Verificado independientemente`.

## 9. Mi trabajo

`WorkItem.inventory_id` sigue siendo la autoridad de periodo para una tarea.

Una tarea vinculada a un inventario histórico debe:

- mostrar el periodo;
- poder filtrarse por ese periodo;
- abrir una ruta explícita o el expediente explícito;
- conservar filtros de la bandeja después de una acción;
- nunca usar una ruta general que pueda reinterpretarla como trabajo del periodo por defecto.

Las tareas sin `inventory_id` se consideran **trabajo transversal**.

## 10. Pruebas obligatorias por superficie

Cada nueva ruta explícita deberá demostrar al menos:

1. acceso permitido para el mismo rol que puede consultar la ruta general equivalente;
2. rechazo de un `inventory_id` perteneciente a otra organización;
3. renderizado del rango exacto de fechas;
4. resultado/datos derivados del inventario solicitado, no del más reciente;
5. enlaces internos que conservan `inventory_id`;
6. ausencia de salto silencioso a una ruta general;
7. comportamiento de inventario cerrado;
8. paridad semántica con la ruta general cuando el `inventory_id` explícito coincide con el periodo por defecto.

## 11. Orden de implementación

La implementación será incremental para reducir riesgo:

### V2.38A · Resultados históricos

Crear `/inventarios/{id}/calculos` de solo lectura, reutilizando el mismo constructor de resultados de `/calculos`.

### V2.38B · Análisis histórico

Crear `/inventarios/{id}/analisis` y enlazarlo desde Resultados explícitos.

### V2.38C · Reducción histórica

Crear `/inventarios/{id}/reduccion` inicialmente como lectura del portafolio del periodo; las mutaciones permanecen bloqueadas hasta revisar cada POST.

### V2.38D · Informes y cierre históricos

Crear vistas explícitas para artefactos y readiness, separando consulta de generación/aprobación.

### V2.38E · Información histórica

Exponer registros, solicitudes y evidencias del periodo explícito. La carga/edición se habilitará solo después de verificar todos los POSTs y redirects.

## 12. Consecuencias

### Positivas

- elimina ambigüedad entre periodo histórico y periodo por defecto;
- permite auditoría longitudinal real;
- hace más útil la plataforma para organizaciones con varios años de inventario;
- evita introducir estado global oculto;
- mejora trazabilidad de enlaces, tareas y documentos;
- prepara comparabilidad interanual sin reinterpretaciones silenciosas.

### Costos

- aumenta el número de rutas;
- obliga a factorizar handlers que hoy resuelven implícitamente el periodo más reciente;
- requiere revisar redirects, CTAs y formularios por superficie;
- exige tests de aislamiento por organización y periodo.

Estos costos se aceptan porque son preferibles a una selección global implícita que pueda mezclar expedientes.

## 13. Criterio de cierre del ADR

La decisión se considera completamente implementada cuando:

- todas las superficies de la matriz que hayan sido habilitadas disponen de rutas explícitas;
- ningún enlace contextual histórico salta silenciosamente al periodo por defecto;
- los tests de aislamiento por organización y periodo están verdes;
- la ruta general continúa representando únicamente el periodo más reciente por defecto;
- no existe estado de sesión denominado o equivalente a “inventario activo”.
