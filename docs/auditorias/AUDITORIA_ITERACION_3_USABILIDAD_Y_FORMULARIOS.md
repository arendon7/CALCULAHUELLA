# Iteración 3 · Usabilidad, formularios y recorridos operativos

## Objetivo

Reducir la carga cognitiva de las pantallas más utilizadas, ordenar las tareas por etapa y ocultar opciones avanzadas hasta que sean necesarias, sin eliminar información ni modificar el motor ambiental.

## Diagnóstico aplicado

La auditoría inicial encontró pantallas con numerosos formularios simultáneos y acciones técnicas que competían visualmente con la tarea principal. Esto dificultaba identificar qué hacer primero, aumentaba el riesgo de diligenciar el formulario equivocado y hacía que la plataforma pareciera más compleja de lo necesario.

La intervención se concentró en cuatro recorridos críticos:

1. Registro y gestión de información.
2. Selección y creación de fuentes.
3. Revisión técnica de una fuente.
4. Control profesional, observaciones y hallazgos.

## Cambios aplicados

### Navegación orientada a tareas

- Se incorporaron barras de acceso directo dentro de cada pantalla crítica.
- Los enlaces llevan a etapas reales de la página y se adaptan al rol activo.
- Se corrigió un vínculo vacío del mapa de fuentes y se reemplazó por un destino funcional.

### Revelado progresivo

- Solicitudes, evidencias, fuentes personalizadas, propuestas de factores y hallazgos nuevos se muestran bajo secciones desplegables.
- Los campos avanzados del dato de actividad —estimación, incertidumbre y notas— permanecen disponibles sin sobrecargar el formulario inicial.
- Factores predeterminados, resultados por gas y memoria de cálculo conservan su contenido completo, pero se consultan bajo demanda.

### Acciones mutuamente excluyentes

- En grupos de edición, revisión y respuesta solo permanece abierta una acción a la vez.
- Al abrir una acción, las demás del mismo grupo se cierran automáticamente.
- Cuando un formulario contiene un campo inválido, su sección se abre para que el usuario pueda corregirlo.
- Los enlaces con ancla abren automáticamente cualquier sección desplegable que contenga el destino.

### Adaptación móvil

- Las barras de tareas y los controles desplegables se reorganizan para pantallas estrechas.
- Se mantiene la jerarquía de acción principal, información avanzada y trazabilidad.

## Resultado medible

Formularios visibles inmediatamente al abrir las cuatro pantallas auditadas:

| Pantalla | Antes | Después | Reducción inicial |
|---|---:|---:|---:|
| Información | 11 | 9 | 18 % |
| Mapa de fuentes | 3 | 2 | 33 % |
| Ficha de fuente | 8 | 4 | 50 % |
| Control profesional | 4 | 3 | 25 % |
| **Total** | **26** | **18** | **31 %** |

Los formularios restantes no fueron eliminados: se conservan dentro de secciones desplegables para mantener capacidad operativa y trazabilidad.

## Validación ejecutada

- 4 pruebas nuevas específicas de usabilidad aprobadas.
- 19 pruebas focalizadas aprobadas en la distribución Mac.
- 34 pruebas focalizadas y de regresión seleccionada aprobadas en Windows durante corridas separadas.
- Las cuatro pantallas críticas renderizan con respuesta 200.
- Recorrido de Cliente, Consultor, Revisor, Verificador y Administrador sin anclas internas rotas.
- Ningún formulario anidado ni identificador HTML duplicado en las pantallas modificadas.
- 76 plantillas Jinja válidas en Mac y 76 en Windows.
- Sintaxis JavaScript validada con Node.js.
- Código de aplicación idéntico en Mac y Windows.

## Alcance preservado

Esta iteración no modifica:

- factores de emisión;
- potenciales de calentamiento global;
- unidades o conversiones;
- fórmulas de cálculo;
- resultados de emisiones;
- datos demostrativos;
- permisos del servidor.

## Limitaciones técnicas conocidas

- La batería histórica completa continúa siendo lenta porque varias pruebas reconstruyen repetidamente la base de datos; las pruebas focalizadas y los recorridos críticos sí concluyeron correctamente.
- El entorno de auditoría bloqueó la navegación automatizada de Chromium hacia el servidor local. La validación visual se realizó mediante renderizado HTML, estructura DOM, comportamiento programado y pruebas funcionales, no mediante capturas automatizadas del navegador.

## Archivos principales modificados

- `app/templates/information.html`
- `app/templates/sources.html`
- `app/templates/source.html`
- `app/templates/control.html`
- `app/static/js/app.js`
- `app/static/css/app.css`
- `tests/test_v100_iteration3_usability.py`

Los cambios fueron replicados en las distribuciones Mac y Windows.

## Siguiente iteración recomendada

**Iteración 4 · Motor metodológico y fórmulas versionadas:** auditar ecuaciones, unidades, GWP, reglas de biogénico, remociones, incertidumbre y gobierno de factores; documentar cada cálculo con fuente, vigencia, versión y memoria reproducible.
