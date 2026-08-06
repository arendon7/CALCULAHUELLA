# Auditoría Iteración 14 — Formularios asistidos y lenguaje claro

## Objetivo
Reducir la carga cognitiva de los formularios principales, traducir conceptos metodológicos sin perder rigor y reforzar la compatibilidad semántica con tecnologías de asistencia.

## Diagnóstico
La Iteración 13 resolvió foco, teclado, diálogos y anuncios generales. Persistían cuatro fricciones:

1. Los campos esenciales y los metodológicos aparecían con el mismo peso visual.
2. Términos como materialidad, incertidumbre, GWP y CO₂e exigían salir de la tarea para consultar la guía.
3. El usuario no recibía una confirmación clara de lo que iba a registrar antes de guardar.
4. El resumen de errores indicaba campos, pero no permitía ir directamente a cada uno.

## Cambios implementados

### 1. Captura guiada asistida
- Se priorizan cuatro decisiones: periodo, cantidad, unidad y soporte.
- Origen y evidencia se presentan como un segundo bloque operativo.
- Estimación, incertidumbre, tipo de soporte y observaciones quedan en una sección técnica opcional.
- Se añadió un resumen dinámico con `aria-live` antes de guardar.
- Todos los campos principales tienen identificadores y ayudas vinculadas mediante `aria-describedby`.

### 2. Configuración de fuentes
- Se separó la identificación operativa de los controles metodológicos.
- “Materialidad” se presenta como “Importancia para el inventario”, conservando el valor técnico interno.
- Se explica la diferencia entre Alcances 1, 2 y 3.
- La exclusión exige una razón específica cuando la fuente no se incluye.

### 3. Diccionario global
- Botón `Aa` disponible desde la barra superior.
- Diez términos esenciales en lenguaje claro.
- Filtro accesible con estado anunciado mediante `aria-live`.
- Acceso alternativo desde la ayuda contextual en móvil.

### 4. Errores y ayudas
- El resumen de errores genera enlaces directos a cada campo inválido.
- Al seleccionar un error se abre la sección plegada correspondiente y se lleva el foco al control.
- Las ayudas incluidas dentro de etiquetas se asocian automáticamente con el control.

## Validación automatizada
- Mac: 414 pruebas aprobadas.
- Windows: 411 pruebas aprobadas y 3 omitidas por ser exclusivas de macOS.
- Migración desde base vacía hasta `20260805_0036` aprobada en ambas distribuciones.
- Auditoría semántica: 10 páginas, 5 roles y 278 controles.
- Controles sin nombre accesible: 0.
- Páginas con identificadores duplicados: 0.
- Cada página auditada contiene un único `h1`.
- Revisión visual: 3 capturas de escritorio y 2 móviles.
- Errores JavaScript durante la revisión visual: 0.

## Impacto metodológico
No se modificaron factores de emisión, versiones GWP, unidades, fórmulas, fuentes de datos ni resultados ambientales.

## Límites de esta certificación
La revisión automatizada no equivale a una certificación WCAG ni sustituye pruebas humanas. Permanecen pendientes:

- VoiceOver con Safari en un equipo Mac físico.
- NVDA con Chrome o Edge en Windows 10/11.
- Sesiones moderadas con usuarios reales de los cinco roles.
- Evaluación de comprensión, tiempo por tarea y tasa de errores.
