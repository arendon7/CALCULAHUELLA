# Auditoría Iteración 12 · UX, recorridos por rol y simplificación visual

## Objetivo

Convertir la amplitud funcional de Calcula tu Huella en una experiencia más fácil de comprender y operar. La revisión se realizó desde cuatro perspectivas: usuario empresarial, consultoría ambiental, revisión/verificación y desarrollo front-end.

La iteración no elimina módulos ni reduce profundidad metodológica. Reorganiza la experiencia para mostrar primero la tarea que corresponde al usuario y dejar el detalle especializado disponible bajo demanda.

## Hallazgos de la revisión

1. La vista esencial seguía siendo demasiado parecida entre roles, aunque sus responsabilidades son distintas.
2. El tablero mostraba una siguiente acción global que podía estar asignada a otro perfil. En particular, el Cliente podía recibir como prioridad una revisión profesional.
3. Datos, solicitudes y evidencias coexistían en una página extensa sin separar claramente las tareas.
4. La ficha de fuente presentaba simultáneamente datos, selección del factor, resultados y memoria de cálculo.
5. El historial de información mostraba hasta 44 registros antes del formulario de captura, generando desplazamiento excesivo en móvil.
6. La navegación móvil dependía del menú lateral y no mantenía accesos rápidos a las tareas frecuentes.
7. El recorrido del inventario mostraba demasiada información de las seis etapas al mismo tiempo.
8. Algunas empresas demo tenían datos suficientes, pero su configuración guiada podía comunicar un estado incompleto y restar credibilidad a la demostración.

## Cambios implementados

### 1. Menú esencial diferente para cada rol

La navegación principal quedó limitada a las decisiones cotidianas de cada perfil:

| Rol | Accesos esenciales | Enfoque |
|---|---:|---|
| Cliente | 6 | Cargar datos, responder solicitudes, aportar soportes y consultar resultados |
| Consultor | 8 | Configurar, recolectar, revisar, cerrar y reducir |
| Revisor | 7 | Calidad, revisión técnica, resultados y expediente de cierre |
| Verificador | 7 | Plan, paquete verificable, metodología, hallazgos y aseguramiento |
| Administrador | 8 | Portafolio, avance, riesgos, resultados, cierre y reducción |

La vista completa continúa disponible y conserva las capacidades especializadas y administrativas.

### 2. Barra de navegación móvil

Se incorporó una barra inferior persistente con cuatro accesos prioritarios del rol y un botón para abrir el menú completo. Esto reduce el número de gestos necesarios para cambiar de tarea en pantallas pequeñas.

### 3. Centro de trabajo más compacto

El tablero ahora integra en un solo bloque:

- huella total del periodo;
- resultados por alcance;
- avance del recorrido;
- nivel de confianza;
- solicitudes pendientes.

Los gráficos, controles metodológicos y análisis detallados permanecen en paneles desplegables. La configuración inicial completa se presenta como contexto compacto y no como otra tarjeta principal.

### 4. Siguiente acción ejecutable por el rol

El Cliente ya no recibe como prioridad una revisión asignada al equipo técnico. Cuando existen solicitudes abiertas, su tablero indica directamente cuántas debe atender, cuál es el criterio de terminación y el enlace para resolverlas. La acción se representa como tarea activa, no como bloqueo crítico.

Los demás perfiles conservan la siguiente puerta técnica o de cierre que les corresponde.

### 5. Datos y evidencias organizados por tarea

La página `/informacion` se dividió en tres tareas excluyentes:

1. registrar datos;
2. solicitar información;
3. gestionar evidencias.

Solo se muestra el panel seleccionado. Las pestañas admiten navegación por teclado, enlace directo mediante hash y recuperación de la sección activa.

El historial presenta por defecto los 12 registros más recientes. El usuario puede abrir los 44 registros del caso demo mediante “Ver historial completo”.

### 6. Ficha de fuente organizada por decisión

La ficha de fuente se dividió en cinco momentos:

1. datos;
2. comparación del factor;
3. factores predeterminados;
4. resultado por gas;
5. memoria de cálculo.

La lista metodológica de seis preguntas se conserva, pero permanece plegada hasta que el usuario entra en la tarea de factor.

### 7. Recorrido del inventario con divulgación progresiva

Las seis etapas se muestran como filas compactas. Como máximo se abre la etapa actual y el resto conserva título, estado y resultado esperado. Las prioridades secundarias quedan plegadas.

### 8. Portafolio demo listo para presentar

Se conservaron las cinco empresas sectoriales y se completó su preparación guiada:

- Greenatics;
- Industrias Andinas;
- Café Sierra Verde;
- Ruta Norte Logística;
- Hotel Bosque Azul.

Cada organización tiene perfil guiado completo, actividades, cálculos y una etapa demostrativa diferenciada. La pantalla del entorno demo presenta primero cuatro indicadores clave y deja métricas secundarias en un detalle desplegable.

## Validación visual

Se generaron y revisaron 25 capturas en escritorio y móvil para los cinco roles. La revisión cubrió:

- centro de trabajo;
- recorrido del inventario;
- datos y evidencias;
- portafolio demo;
- comportamiento móvil del Cliente y Administrador.

La evidencia se conserva en `EVIDENCIA_VISUAL_ITERACION_12/`.

## Validación técnica

### macOS

- 404 pruebas aprobadas.
- 0 fallos.

### Windows

- 401 pruebas aprobadas.
- 3 omitidas exclusivamente por corresponder al ciclo de vida macOS.
- 0 fallos.

### Controles adicionales

- 166 archivos Python revisados.
- 80 plantillas HTML conservadas.
- Código de aplicación y pruebas sincronizado entre Mac y Windows.
- JavaScript validado sintácticamente.
- 25 capturas de revisión visual.
- Pruebas nuevas para navegación por rol, barra móvil, acción del Cliente, paneles por tarea, límite de historial, recorrido y preparación del demo.
- Los archivos `app/calculations.py` y `app/land_removals.py` conservan hashes idénticos a la Iteración 11.
- No se modificaron factores de emisión, GWP, fórmulas, unidades ni resultados ambientales.

## Resultado

La plataforma mantiene su profundidad profesional, pero deja de presentar la arquitectura interna como si fuera el recorrido del usuario. Cada perfil ve primero su trabajo, el Cliente recibe acciones que realmente puede completar y las páginas operativas extensas se convierten en espacios por tarea.

El entorno demo ya comunica empresas activas y procesos en distintas etapas, en lugar de una aplicación vacía o permanentemente “en configuración”.

## Pendientes recomendados

1. Pruebas observadas con usuarios externos de cada rol.
2. Auditoría formal WCAG 2.2 AA y navegación completa con lector de pantalla.
3. Microcopias y ayuda contextual en formularios de mayor complejidad.
4. Analítica de navegación y abandono para validar el orden de tareas con uso real.
5. Recorrido interactivo opcional para el primer ingreso de cada rol.
