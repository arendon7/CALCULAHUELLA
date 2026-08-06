# Auditoría Iteración 8 · Huella de producto, proyectos de mitigación y aseguramiento

**Fecha:** 5 de agosto de 2026  
**Versión base:** Iteración 7 · tierras, remociones y circularidad  
**Alcance:** ampliación metodológica y funcional sin modificar el motor del inventario corporativo.

## 1. Objetivo

Cerrar tres brechas detectadas en la auditoría inicial:

1. cuantificar huellas de producto con unidad declarada, flujo de referencia y etapas de ciclo de vida;
2. gestionar proyectos de mitigación mediante línea base, escenario de proyecto, fugas, remociones y monitoreo;
3. distinguir revisión interna, validación y verificación independiente mediante encargos controlados.

## 2. Referentes metodológicos

- **ISO 14067:2018:** cuantificación y reporte de huella de carbono de productos, coherente con evaluación de ciclo de vida.
- **GHG Protocol Product Life Cycle Accounting and Reporting Standard:** contabilidad de emisiones durante el ciclo de vida y análisis de oportunidades de reducción.
- **ISO 14064-2:2019:** cuantificación, monitoreo y reporte de reducciones de emisiones o aumentos de remociones a nivel de proyecto.
- **GHG Protocol for Project Accounting:** comparación de línea base y escenario de proyecto, con tratamiento de efectos secundarios y atribución.
- **ISO 14064-3:2019:** validación y verificación de declaraciones de GEI aplicables a organizaciones, proyectos y productos.

Fuentes oficiales consultadas:

- https://www.iso.org/standard/71206.html
- https://www.iso.org/standard/66454.html
- https://www.iso.org/standard/66455.html
- https://ghgprotocol.org/product-standard
- https://ghgprotocol.org/project-protocol

ISO mantiene ISO 14067:2018 como versión vigente. ISO 14064-2:2019 continúa publicada, aunque existe un nuevo trabajo de revisión en desarrollo; por tanto, la plataforma registra la versión utilizada y deberá vigilar futuras sustituciones.

## 3. Implementación

### 3.1 Huella de producto

Se creó un expediente independiente con:

- producto, código, unidad declarada y flujo de referencia;
- límite: cuna–puerta, cuna–tumba, puerta–puerta o huella parcial;
- metodología, PCR o regla sectorial, asignación, corte y tratamiento biogénico;
- etapas A1, A2, A3, A4, B1, B2, C1, biogénico/uso de la tierra y otros procesos;
- actividad, unidad, factor, unidad de salida, geografía, año, incertidumbre y evidencia;
- normalización exclusiva de `g CO2e`, `kg CO2e` y `t CO2e`;
- presentación separada de emisiones, remociones, carbono almacenado y emisiones evitadas;
- bloqueo de aprobación cuando faltan etapas mínimas para el límite declarado.

**Fórmula de etapa:**

`Emisiones etapa [tCO2e] = actividad × factor × conversión de unidad de salida`

**Resultado por unidad declarada:**

`CFP = (emisiones brutas − remociones elegibles) / flujo de referencia`

El carbono almacenado y las emisiones evitadas permanecen informativos y no se descuentan automáticamente.

### 3.2 Proyectos de mitigación

Se creó un expediente separado del inventario corporativo con:

- escenario de línea base y escenario del proyecto;
- adicionalidad, plan de monitoreo, fuentes de fuga, titularidad y doble conteo;
- estimación inicial y periodos de monitoreo;
- evidencia, incertidumbre y revisión por periodo;
- prohibición de incorporar automáticamente reducciones como emisiones negativas del inventario.

**Fórmula:**

`Reducción = línea base − emisiones del proyecto − fugas + remociones`

La fórmula admite resultados negativos para revelar un desempeño peor que la línea base; no los oculta ni los fuerza a cero.

### 3.3 Aseguramiento independiente

Se creó un expediente de validación/verificación con:

- sujeto: inventario corporativo, huella de producto o proyecto de mitigación;
- validación o verificación;
- estándar, nivel limitado o razonable y materialidad;
- criterios, alcance, organismo, verificador líder, independencia y competencia;
- hallazgos menores, mayores o críticos;
- respuestas de gestión y conclusiones del verificador;
- bloqueo de declaración mientras existan hallazgos mayores o críticos abiertos;
- opinión: sin salvedades, con salvedades, adversa o abstención;
- declaración fechada y auditada.

La plataforma no acredita al organismo ni convierte la revisión interna en verificación independiente.

## 4. Navegación y reducción de duplicidades

- El menú principal reemplaza “Portal del verificador” por **Aseguramiento independiente**.
- La antigua ruta `/verificacion` permanece como mesa histórica de hallazgos y generación de paquete reproducible, accesible desde el nuevo expediente.
- Huella de producto y proyectos de mitigación aparecen como capacidades avanzadas, evitando sobrecargar el recorrido diario del inventario.

## 5. Persistencia y trazabilidad

Migración nueva: **`20260805_0036`**.

Tablas nuevas:

1. `product_footprint_studies`
2. `product_lifecycle_stages`
3. `mitigation_projects`
4. `mitigation_monitoring_periods`
5. `assurance_engagements`
6. `assurance_findings`

El paquete ZIP de verificación incorpora seis nuevos archivos CSV para producto, etapas, proyectos, monitoreo, encargos y hallazgos.

## 6. Compatibilidad de resultados

Se compararon la Iteración 7 y la Iteración 8 desde bases demostrativas nuevas:

- **200 componentes de cálculo:** idénticos.
- **25 fuentes:** idénticas.
- Hash SHA-256 del conjunto de resultados: `7005da53cb6e9dd56275279b3b9388203b7d3167d7ba1afe2106c8d50cf61b88` en ambas versiones.

No se modificaron factores, GWP, conversiones del inventario, emisiones por fuente ni resultados corporativos.

## 7. Validaciones ejecutadas

- 43 pruebas focalizadas aprobadas en la copia Mac.
- Migración completa desde base vacía hasta `20260805_0036`.
- Generación histórica del paquete de verificación aprobada con los nuevos anexos.
- Arquitectura actualizada a 12 módulos de persistencia y 120 tablas.
- Rutas nuevas verificadas por roles y APIs.
- Plantillas Jinja, sintaxis Python y paridad Mac/Windows verificadas antes del empaquetado.

## 8. Limitaciones conscientes

- No se implementó una base LCA completa con procesos unitarios interconectados, matrices tecnosféricas ni importación automática de bases comerciales.
- No se declara conformidad ISO automática ni certificación de una EPD.
- La PCR debe ser seleccionada y validada por el equipo profesional.
- Los proyectos no generan créditos, offsets ni unidades transables.
- La validación/verificación requiere un tercero competente y, cuando aplique, acreditado bajo el programa correspondiente.
- Las revisiones futuras de ISO 14067 e ISO 14064-2 deben vigilarse mediante el gobierno metodológico.

## 9. Próxima iteración recomendada

**Iteración 9: arquitectura, rendimiento, pruebas y seguridad.**

Prioridades:

- acelerar la suite completa y eliminar reconstrucciones repetidas de base de datos;
- pruebas end-to-end de navegación y formularios en navegador real;
- exportaciones formales de huella de producto, documento de diseño de proyecto y declaración de aseguramiento;
- control de concurrencia, cargas masivas y rendimiento multiempresa;
- endurecimiento de seguridad y revisión independiente antes de producción pública.
