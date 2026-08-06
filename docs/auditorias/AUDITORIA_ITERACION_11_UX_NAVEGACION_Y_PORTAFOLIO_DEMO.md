# Auditoría Iteración 11 · UX, navegación y portafolio demostrativo

## Objetivo

Reducir la carga cognitiva de la plataforma, hacer más claro el siguiente paso de cada usuario y convertir el entorno demo en una demostración multisectorial con información suficiente para recorrer el ciclo completo de un inventario.

## Diagnóstico inicial

La vista esencial todavía exponía demasiados módulos y mezclaba tareas operativas, metodología, administración y herramientas especializadas. El tablero repetía información de avance en varias zonas y las empresas demostrativas no alcanzaban a mostrar con claridad diferentes niveles de madurez.

## Cambios implementados

### 1. Navegación esencial orientada a tareas

La vista esencial quedó reducida a ocho o nueve accesos según el rol:

1. Centro de trabajo.
2. Continuar recorrido.
3. Inventarios.
4. Capturar datos, cuando el rol puede hacerlo.
5. Datos y evidencias.
6. Calidad y revisión.
7. Resultados.
8. Cierre e informes.
9. Plan de reducción.

La vista completa conserva entre 27 y 56 accesos según permisos. Las funciones avanzadas no fueron eliminadas; se trasladaron a la vista completa y se incorporó búsqueda dentro del menú.

### 2. Cambio rápido de empresa

Se añadió un selector de organización en la barra superior. Los usuarios con membresía en varias empresas pueden cambiar de caso sin regresar al portafolio o a una pantalla administrativa.

### 3. Tablero con divulgación progresiva

El tablero muestra primero:

- organización y periodo activos;
- caso demostrativo y propósito;
- siguiente acción;
- estado del proceso;
- indicadores de emisiones.

Los controles metodológicos, gráficos, fuentes principales y solicitudes quedan en paneles desplegables. Esto mantiene la profundidad profesional sin saturar la primera lectura.

### 4. Portafolio demo multisectorial

Se incorporaron cinco empresas con procesos y estados diferentes:

| Empresa | Sector | Etapa demostrada | Contenido principal |
|---|---|---|---|
| Greenatics | Gestión de residuos y fertilizantes | Recolección y revisión | Plantas, compostaje, digestión anaerobia, energía y logística |
| Industrias Andinas | Manufactura | Cálculo y cierre | Multisede, combustibles, refrigerantes y cadena de valor |
| Café Sierra Verde | Agroindustria | Recolección | Fertilización, beneficio, maquinaria, residuos y transporte |
| Ruta Norte Logística | Transporte y logística | Revisión técnica | Flota, centros logísticos, refrigeración y tonelada-kilómetro |
| Hotel Bosque Azul | Servicios y hotelería | Inventario aprobado | Energía, gas, refrigerantes, residuos, resultados y reducción |

Cada empresa incluye perfil, diagnóstico, inventario, fuentes, registros de actividad, cálculos, evidencias, solicitudes, hallazgos y plan de implementación.

## Cobertura demostrativa

- 5 empresas.
- 5 sectores.
- 14 instalaciones.
- 6 inventarios.
- 37 fuentes.
- 290 registros de actividad.
- 338 cálculos.
- 19 evidencias.
- 17 solicitudes.
- 15 observaciones.
- 5 planes de implementación.
- Etapas cubiertas: recolección, cálculo/cierre, revisión y entrega aprobada.

## Controles técnicos

- La preparación del demo continúa siendo idempotente.
- Los usuarios demo reciben membresías válidas para las cinco empresas.
- El cambio de organización respeta control de acceso y sesión.
- No se modificaron factores, GWP, fórmulas ni resultados metodológicos existentes.
- La suite completa se ejecuta en procesos aislados para evitar falsos bloqueos por acumulación de estado.

## Validación

### macOS

- 397 pruebas aprobadas.
- 0 fallos.

### Windows

- 394 pruebas aprobadas.
- 3 omitidas por corresponder exclusivamente a macOS.
- 0 fallos.

### Validaciones adicionales

- Código `app` y pruebas sincronizados entre Mac y Windows.
- Cinco historias demo distintas y rutas de acción propias.
- Menú esencial limitado a ocho o nueve accesos en todos los roles.
- Cambio de empresa verificado mediante recorrido autenticado.
- Plantillas y código Python compilados antes del empaquetado.

## Resultado

La plataforma conserva su profundidad técnica, pero el usuario ya no debe interpretar decenas de módulos para comenzar. El entorno demo permite explicar el producto mediante casos completos, distintos y navegables, en lugar de pantallas vacías o estados repetidos.

## Próximas mejoras recomendadas

1. Pruebas de usabilidad observadas con usuarios externos.
2. Accesibilidad formal WCAG 2.2 AA.
3. Personalización del inicio según rol y tarea frecuente.
4. Recorridos guiados opcionales para el primer ingreso.
5. Analítica de navegación para detectar abandonos y pantallas poco utilizadas.
