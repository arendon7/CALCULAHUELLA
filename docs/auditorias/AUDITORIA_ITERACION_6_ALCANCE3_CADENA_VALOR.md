# Auditoría Iteración 6
## Alcance 3, cadena de valor y gestión de proveedores

**Fecha:** 5 de agosto de 2026  
**Versión base:** Iteración 5 · Biblioteca y gobierno de factores  
**Alcance:** mejoras funcionales, metodológicas y de trazabilidad sin modificar resultados ambientales aceptados.

## 1. Objetivo

Convertir el módulo existente de proveedores en una capa estructurada de gestión de Alcance 3 que permita:

- examinar las quince categorías del GHG Protocol;
- distinguir actividades aguas arriba y aguas abajo;
- documentar materialidad, responsables y estrategia de obtención de datos;
- validar matemáticamente la información remitida por proveedores;
- evaluar calidad, evidencia y límites;
- prevenir duplicidades y solapamientos antes de aprobar datos.

## 2. Diagnóstico inicial

La versión anterior ya disponía de campañas, solicitudes, respuestas y una fuente agregada de proveedores. La auditoría detectó estas brechas:

1. No existía un screening persistente de las quince categorías.
2. Alcance 3 se presentaba principalmente como una fuente agregada, sin mapa de materialidad completo.
3. Las respuestas podían contener combinaciones incoherentes de actividad, factor y unidad.
4. Faltaban controles explícitos de límites, metodología y evidencia.
5. No se impedía aprobar dos respuestas equivalentes para la misma categoría, proveedor y producto.
6. La calidad se expresaba de forma limitada y no como un pasaporte trazable.
7. La exportación no incluía el screening integral de categorías.

## 3. Mejoras implementadas

### 3.1 Catálogo canónico de Alcance 3

Se creó un catálogo único con las categorías C1 a C15:

- ocho categorías aguas arriba;
- siete categorías aguas abajo;
- nombre canónico, dirección, métodos sugeridos, límite mínimo y prioridad de datos;
- normalización de alias para evitar categorías duplicadas por diferencias de redacción.

### 3.2 Screening persistente

Se incorporó la tabla `scope3_category_assessments`, vinculada a cada inventario. Cada categoría conserva:

- estado: Pendiente, Material, No material o No aplica;
- puntuación de relevancia;
- justificación;
- responsable;
- estrategia de datos;
- usuario y fecha de actualización.

La migración Alembic `20260805_0034` fue probada desde una base limpia hasta `head`.

### 3.3 Validación por método

Las respuestas de proveedores se validan antes de ser aceptadas o aprobadas:

- **Factor por unidad:** exige actividad y factor positivos, numerador en kg CO2e y denominadores compatibles.
- **Gasto:** exige gasto y factor positivos y la unidad `kg CO2e/COP`.
- **Huella total:** exige emisiones positivas y documentadas.
- Se advierte cuando la cantidad respondida difiere más de 10 % de la solicitada.
- Metodología y límite organizacional o de ciclo de vida son obligatorios para aprobación.

### 3.4 Pasaporte de calidad

Cada respuesta obtiene una evaluación de 0 a 100 y un nivel A–D, considerando:

- especificidad del método;
- consistencia de unidades y cantidades;
- metodología declarada;
- límite cubierto;
- evidencia aportada;
- dependencia de datos monetarios o secundarios.

La puntuación no reemplaza la revisión profesional; sirve como señal de priorización y trazabilidad.

### 3.5 Prevención de doble conteo

Se añadieron dos controles:

- bloqueo de aprobación cuando ya existe otra respuesta aprobada para la misma categoría, proveedor y producto o servicio;
- advertencias cuando una categoría consolidada desde proveedores puede solaparse con fuentes manuales de Alcance 3.

### 3.6 Interfaz, API y Excel

El módulo ahora presenta:

- matriz de las quince categorías;
- métricas de categorías evaluadas y materiales;
- emisiones aguas arriba y aguas abajo;
- cobertura y calidad de proveedores;
- alertas metodológicas y de duplicidad;
- formularios de evaluación por categoría;
- API `/api/cadena-valor/resumen`;
- archivo Excel con hojas `Solicitudes proveedores` y `Screening 15 categorías`.

## 4. Base metodológica

La estructura sigue el **GHG Protocol Corporate Value Chain (Scope 3) Standard** y su guía de cálculo, que organizan las emisiones de cadena de valor en quince categorías y contemplan métodos basados en información específica del proveedor, actividad física y gasto.

Referencias oficiales:

- https://ghgprotocol.org/scope-3-calculation-guidance-2
- https://ghgprotocol.org/corporate-value-chain-scope-3-standard
- https://ghgprotocol.org/scope-3-frequently-asked-questions-0

## 5. Validaciones ejecutadas

### Pruebas funcionales y metodológicas

- 6 pruebas nuevas de Iteración 6 aprobadas.
- 14 pruebas de regresión de Iteraciones 4 y 5 aprobadas.
- 13 pruebas de roles, navegación, usabilidad y cadena de suministro aprobadas.
- **Total focalizado: 33 pruebas aprobadas.**

Una ejecución conjunta extensa excedió el tiempo disponible debido a que varias pruebas históricas reconstruyen repetidamente la base de datos. No mostró fallos antes del límite; los grupos fueron ejecutados por separado y aprobaron.

### Integridad numérica

Comparación Iteración 5 vs. Iteración 6:

- **200/200 componentes de cálculo idénticos.**
- Total corporativo idéntico: **578,375304 tCO2e**.
- Resultados por alcance idénticos.
- Campos numéricos y contables de las siete fuentes idénticos.
- Único cambio descriptivo: la fuente agregada pasó de `Bienes y servicios adquiridos` a `Cadena de valor consolidada desde proveedores` para evitar interpretar que cubre exclusivamente C1.

## 6. Límites deliberados

Esta iteración no pretende todavía:

- sustituir la evaluación profesional de materialidad;
- calcular automáticamente cada categoría mediante motores sectoriales independientes;
- descomponer métodos híbridos en múltiples componentes dentro del portal;
- incorporar factores colombianos de Alcance 3 sin fuente aprobada y pasaporte completo;
- definir una política corporativa definitiva de recálculo del año base para Alcance 3;
- eliminar automáticamente fuentes manuales potencialmente solapadas sin revisión humana.

## 7. Riesgos residuales y siguientes mejoras

1. Formalizar una política configurable de materialidad y exclusiones.
2. Desarrollar calculadoras específicas por categoría prioritaria.
3. Incorporar trazabilidad de productos, rutas, activos arrendados, uso y fin de vida.
4. Ampliar el portal para métodos híbridos y archivos estructurados de proveedores.
5. Enriquecer la biblioteca colombiana con factores secundarios revisados.
6. Vincular acciones de reducción y compromisos de proveedores a cada categoría.

## 8. Conclusión

La Iteración 6 convierte la cadena de valor en un proceso gobernado, verificable y progresivo. La plataforma ya permite examinar todas las categorías, documentar decisiones, controlar respuestas de proveedores y detectar duplicidades, manteniendo intactos los resultados aprobados de la versión anterior.

**Siguiente iteración recomendada:** tierras, remociones, emisiones biogénicas y circularidad.
