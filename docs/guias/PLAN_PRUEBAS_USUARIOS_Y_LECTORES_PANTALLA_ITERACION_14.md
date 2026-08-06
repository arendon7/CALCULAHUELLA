# Plan de pruebas con usuarios y lectores de pantalla

## Propósito
Validar que los recorridos sean comprensibles, operables y eficientes para personas con distintos niveles de conocimiento ambiental.

## Participantes recomendados
- 2 responsables de información de empresas cliente.
- 2 consultores ambientales.
- 1 revisor metodológico.
- 1 verificador independiente.
- 1 administrador de portafolio.
- Al menos 1 usuario habitual de VoiceOver y 1 de NVDA.

## Tareas por rol

### Cliente
1. Identificar la empresa y periodo activos.
2. Registrar un dato de actividad con soporte.
3. Corregir un campo inválido usando el resumen de errores.
4. Consultar “incertidumbre” en el diccionario.

### Consultor
1. Configurar una fuente.
2. Definir alcance, sede, responsable y unidad.
3. Abrir controles metodológicos y justificar una exclusión.
4. Continuar el recorrido del inventario.

### Revisor
1. Encontrar la prioridad de revisión.
2. Abrir un dato y su soporte.
3. Localizar alertas metodológicas sin usar la vista completa.

### Verificador
1. Abrir el plan de verificación.
2. Navegar tablas con encabezados y regiones identificadas.
3. Revisar un hallazgo y regresar al contexto anterior.

### Administrador
1. Cambiar de empresa.
2. Regresar al portafolio.
3. Activar la vista completa y buscar un módulo.

## Matriz VoiceOver
- Equipo: macOS y Safari actuales.
- Navegación: `Control + Option + flechas`.
- Confirmar: landmarks, títulos, formularios, fieldsets, ayudas, diálogos y devolución de foco.
- Verificar que el resumen dinámico de captura sea anunciado una sola vez por cambio relevante.

## Matriz NVDA
- Equipo: Windows 10/11 con Chrome o Edge.
- Navegación: modo exploración, `H`, `F`, `D`, `T` y Tab.
- Confirmar: títulos, formularios, diálogos, tablas, estados y enlaces del resumen de errores.
- Verificar que las secciones técnicas plegadas informen estado expandido/contraído.

## Métricas
- Tasa de finalización por tarea.
- Tiempo por tarea.
- Número de retrocesos o aperturas innecesarias.
- Errores antes de guardar.
- Solicitudes de ayuda.
- Comprensión de “alcance”, “factor”, “CO₂e”, “materialidad” e “incertidumbre”.
- Puntuación de facilidad de 1 a 5.

## Criterios de aceptación
- 90 % de tareas esenciales completadas sin asistencia directa.
- Ningún bloqueo de teclado o lector de pantalla.
- 80 % de participantes interpreta correctamente los cinco términos críticos.
- Menos de dos errores promedio por registro de actividad.
- Ninguna pérdida de datos al abrir o cerrar secciones avanzadas.
