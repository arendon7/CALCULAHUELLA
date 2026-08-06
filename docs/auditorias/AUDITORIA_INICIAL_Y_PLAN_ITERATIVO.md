# Auditoría inicial y plan iterativo · Iteración 1

Fecha: 5 de agosto de 2026  
Base: Calcula tu Huella V1.0.0 final dual Mac/Windows

## Alcance de la auditoría

Se revisaron estructura, rutas HTTP, navegación por roles, plantillas, formularios, permisos, bloqueo de inventarios, motor de cálculo, biblioteca de factores, documentación metodológica, pruebas automatizadas y limpieza del paquete.

## Dimensión técnica observada

- 316 rutas HTTP registradas.
- 68 plantillas HTML.
- 112 tablas ORM.
- 337 pruebas automatizadas recolectadas.
- Pantallas críticas con alta densidad: núcleo metodológico (34 formularios), metodología (29), consolidación (29), divulgación climática (25) y detalle de fuente (hasta 21).
- La suite integral reconstruye y repuebla la base con frecuencia por caso de prueba; por ello no termina en un tiempo práctico de retroalimentación.

## Validación posterior a las correcciones

- Pruebas focalizadas nuevas: 4 de 4 aprobadas en MAC y 4 de 4 en WINDOWS.
- Código Python analizado sintácticamente: 202 archivos sin errores.
- Carpetas `MAC/app` y `WINDOWS/app`: idénticas después de la sincronización.
- Recorrido autenticado de 500 URL por rol: no quedaron respuestas 404, 409 ni 422 en Consultor o Cliente.
- Sigue pendiente reducir enlaces visibles que terminan en 403 para el rol Cliente; el principal origen es el acceso contextual a metodología/factores y páginas internas.

## Correcciones aplicadas en esta iteración

1. Se corrigió el enlace metodológico `/metodologia-cierre`, que no existía, por `/metodologia/cierre`.
2. Se corrigió la codificación HTML del parámetro `copy_record_id` en “Usar como referencia”, que generaba respuestas 422.
3. El nombre de la organización ya no dirige a `/portafolio` cuando el rol no tiene permiso para gestionarlo.
4. Los inventarios cerrados ya no ofrecen botones de edición incompatibles con su estado; ahora remiten al control de versión.
5. La puerta de alistamiento metodológico evita dirigir un inventario cerrado a una pantalla de edición bloqueada.
6. Se eliminaron metadatos `__MACOSX`, cachés Python, `.pytest_cache`, archivos `.pyc` y `.DS_Store` del entregable.
7. Se mantuvieron sincronizadas las correcciones en las carpetas MAC y WINDOWS.

## Hallazgos prioritarios pendientes

### Funcionales y UX

- Varias pantallas concentran entre 20 y 34 formularios y deben dividirse en flujos por tarea.
- Debe completarse una auditoría de enlaces contextuales por rol para evitar accesos visibles que terminan en 403.
- Existen controles de formulario sin asociación explícita con etiquetas, especialmente en metodología, cierre y consolidación.
- La jerarquía de encabezados es irregular en varias pantallas operativas.
- Los estados cerrados, en revisión y aprobados necesitan acciones y mensajes consistentes en todo el producto.

### Ingeniería de software

- `main.py` y `database.py` concentran demasiadas responsabilidades y deben separarse gradualmente por dominios.
- La suite de pruebas reconstruye una base de 112 tablas para numerosos casos y no entrega retroalimentación en un tiempo práctico.
- Deben existir pruebas rápidas de navegación, permisos, enlaces internos y estados bloqueados antes de ejecutar la suite integral.
- Se debe automatizar la comparación de las copias MAC y WINDOWS para impedir divergencias.

### Ingeniería ambiental y metodología

- El GWP debe seleccionarse mediante un catálogo versionado y validado, sin valores implícitos ante textos no reconocidos.
- La incertidumbre actual, basada en suma cuadrática y rangos simétricos, debe conservarse como método básico y complementarse con distribuciones, asimetría, correlación y Monte Carlo cuando aplique.
- La calidad del dato debe evaluarse por dimensiones: confiabilidad, completitud, representatividad temporal, geográfica y tecnológica.
- La biblioteca de factores requiere gobernanza por vigencia, jurisdicción, estado oficial/preliminar, tecnología, fuente primaria y trazabilidad de cambios.
- Debe ampliarse Alcance 3 a una matriz completa de categorías, métodos, exclusiones, materialidad y cobertura.
- El módulo de tierras, remociones y almacenamiento debe evolucionar de preparación documental a contabilidad completa cuando sea aplicable.
- Deben incorporarse rutas específicas para huella de producto, proyectos de reducción/remoción y verificación.

## Ciclo propuesto

1. **Estabilización funcional:** enlaces, permisos visibles, bloqueos, errores 4xx y pruebas rápidas.
2. **Simplificación UX por rol:** dividir megapantallas, recorridos por tarea, formularios progresivos y ayuda contextual.
3. **Núcleo metodológico:** GWP, fórmulas versionadas, incertidumbre avanzada, calidad del dato y reglas de recalculo.
4. **Biblioteca Colombia:** electricidad anual, combustibles, transporte, residuos, aguas residuales, suelos y fertilizantes con estados formal/preliminar.
5. **Alcance 3 y proveedores:** 15 categorías, screening, asignaciones, evidencias, cuestionarios e importaciones.
6. **Tierras, remociones y circularidad:** carbono biogénico, existencias, permanencia, reversión y separación de emisiones evitadas.
7. **Producto, proyectos y aseguramiento:** ISO 14067, ISO 14064-2, ISO 14064-3 e ISO/TS 14064-4.
8. **Reportes y decisiones:** informes auditables, tableros ejecutivos, comparabilidad, metas y portafolio de reducción.
9. **Arquitectura, seguridad y rendimiento:** modularización, migraciones, pruebas eficientes, observabilidad, respaldo y endurecimiento.
10. **Certificación dual y piloto multiempresa:** pruebas físicas Mac/Windows, instalación, actualización, recuperación y validación con empresas reales.

## Criterio de entrega por iteración

Cada iteración debe cerrar con: código sincronizado Mac/Windows, pruebas focalizadas, recorrido por roles, inventario de cambios, limitaciones conocidas y ZIP autocontenido completo.
