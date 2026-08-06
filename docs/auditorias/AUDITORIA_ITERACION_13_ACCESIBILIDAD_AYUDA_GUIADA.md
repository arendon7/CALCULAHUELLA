# Auditoría Iteración 13 · Accesibilidad, microcopias y ayuda guiada

**Proyecto:** Calcula tu Huella  
**Fecha:** 5 de agosto de 2026  
**Base intervenida:** Iteración 12 · UX y recorridos por rol

## Objetivo

Reducir barreras de uso para personas que navegan con teclado, lectores de pantalla, dispositivos móviles o menor familiaridad técnica. La intervención se concentró en la capa de experiencia y no modificó el motor ambiental.

## Mejoras incorporadas

### 1. Navegación y estructura accesible

- Idioma del documento definido como `es-CO`.
- Enlaces de salto al contenido y a la navegación principal.
- Regiones semánticas y etiquetas accesibles para navegación, contenido y avisos.
- Identificación de la página activa mediante `aria-current`.
- Foco visible y consistente para teclado.
- Tamaños mínimos de interacción reforzados en controles táctiles.
- Menú móvil con cierre por `Escape`, devolución de foco y bloqueo temporal del contenido de fondo.

### 2. Formularios y mensajes de error

- Campos obligatorios identificados visualmente y mediante atributos accesibles.
- Campos inválidos marcados con `aria-invalid`.
- Resumen global de errores con enlaces al control correspondiente.
- Mensajes importantes anunciados mediante regiones `aria-live`.
- Conservación del foco y de la referencia contextual después de un error.

### 3. Ayuda contextual

- Botón de ayuda disponible desde la barra superior.
- Diálogo accesible con explicación específica para la página y el rol.
- Instrucciones breves, ordenadas y enfocadas en la siguiente tarea.
- Acceso permanente a la guía completa sin duplicar botones dentro del tablero.

### 4. Recorrido de primer ingreso

- Recorrido de cuatro pasos reutilizable.
- Contenido adaptado a Cliente, Consultor, Revisor, Verificador y Administrador.
- Apertura automática únicamente en el primer ingreso de cada rol y navegador.
- Posibilidad de omitir, retroceder, avanzar y volver a abrir el recorrido.
- Estado almacenado localmente, sin alterar datos empresariales.

### 5. Reducción de carga visual

- Acciones secundarias de importación y plantillas agrupadas bajo “Otras formas de carga”.
- Acción primaria renombrada como “Registrar un dato”.
- En captura guiada, la acción principal se expresa como “Ver datos y evidencias”.
- Eliminación del acceso redundante “Consultar guía” del tablero.
- Tablas extensas convertidas en regiones navegables con nombre y descripción.

### 6. Preferencias del usuario

- Respeto de `prefers-reduced-motion`.
- Soporte básico de modos de alto contraste mediante `forced-colors`.
- Diálogos nativos con control de foco.
- Botones con nombre accesible verificable.

## Alcance técnico

Archivos funcionales modificados:

- `app/templates/base.html`
- `app/templates/dashboard.html`
- `app/templates/information.html`
- `app/templates/guided_capture.html`
- `app/static/css/app.css`
- `app/static/js/app.js`
- `scripts/run_test_tier.py` (aislamiento reforzado para módulos con múltiples ciclos de aplicación)

Pruebas incorporadas:

- `tests/test_iteration13_accessibility_help.py`

Se actualizó una prueba histórica para verificar la semántica del control de inventario sin depender de una secuencia HTML incompatible con los nuevos atributos ARIA.

## Integridad metodológica

- 112 archivos Python del código de aplicación comparados con la Iteración 12.
- **0 archivos Python del motor modificados.**
- Sin cambios en factores de emisión, GWP, conversiones, fórmulas, inventarios o resultados.
- La intervención se limita a plantillas, CSS, JavaScript y pruebas de interfaz.

## Validación

- Mac: **409 pruebas aprobadas**.
- Windows: **406 pruebas aprobadas y 3 omitidas por corresponder exclusivamente a macOS**.
- Cinco pruebas nuevas específicas de accesibilidad aprobadas en ambas distribuciones.
- Ejecución `smoke` del lanzador final: 9 aprobadas y 400 deseleccionadas por plataforma.
- JavaScript validado sintácticamente con Node.
- CSS validado estructuralmente.
- Recorrido Playwright aprobado en escritorio y móvil.
- Revisión visual de primer ingreso, ayuda contextual, menú móvil, formulario inválido y agrupación de acciones.
- Aplicación Mac y Windows sincronizada.

## Referencia de accesibilidad

La implementación se diseñó tomando WCAG 2.2 y las prácticas de accesibilidad de WAI-ARIA como referencia. Esta iteración **no constituye una certificación formal de conformidad WCAG**. Para una declaración externa todavía se requiere evaluación manual con tecnologías de asistencia, pruebas con usuarios y auditoría independiente.

## Pendientes recomendados

1. Pruebas físicas con VoiceOver, NVDA y TalkBack.
2. Evaluación manual completa de contraste por estado y componente.
3. Pruebas de zoom al 200 % y 400 % en dispositivos reales.
4. Sesiones con usuarios Cliente y Consultor sin capacitación previa.
5. Auditoría independiente antes de declarar conformidad WCAG.

## Conclusión

La plataforma conserva su profundidad técnica, pero ofrece ahora una entrada más comprensible, operable por teclado y acompañada por ayuda contextual. El resultado reduce barreras sin simplificar indebidamente la metodología ni alterar los cálculos ambientales.
