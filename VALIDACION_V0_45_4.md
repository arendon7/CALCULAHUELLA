# Validación V0.45.4 — primer inventario y carga inicial

## Objetivo

Reducir la fricción entre crear un inventario, configurar sus fuentes y registrar el primer dato, sin alterar metodología, motores de cálculo, factores, fórmulas, modelos, migraciones ni datos demostrativos.

## Cambios verificados

- Asistente de creación de inventario organizado en cuatro pasos.
- Tres paquetes iniciales de fuentes: servicios y oficinas, operación productiva y gestión de residuos.
- Creación idempotente de fuentes, con prevención de duplicados.
- Configuración editable de alcance, categoría, sede, responsable, materialidad, frecuencia, unidad e inclusión.
- Exclusiones condicionadas a una justificación documentada.
- Ruta guiada desde el mapa de fuentes hacia la primera carga y su evidencia.
- Sugerencia de periodo inicial y unidad preferida según la fuente seleccionada.
- Compatibilidad con inventarios y fuentes existentes.
- Aplicación, instalador, manifiesto de marca y ciclo de vida macOS alineados en 0.45.4.

## Validaciones ejecutadas

- 64 plantillas Jinja compiladas sin errores.
- Código Python compilado correctamente.
- JavaScript principal validado con `node --check`.
- Scripts `.sh` y `.command` validados con `bash -n`.
- 87 pruebas focalizadas aprobadas en inventarios, fuentes, carga inicial, experiencia, autenticación, persistencia, arquitectura, certificación, entorno demo, metodología, piloto y operaciones.
- Prueba HTTP final aprobada para salud, acceso, creación de inventario, mapa de fuentes, carga de información y detalle de fuente.
- API de salud comprobada con versión 0.45.4.
- 279 rutas registradas, 71 rutas propias de dominio y 109 tablas/modelos sin cambios estructurales.

## Regresión completa

La suite histórica monolítica reinicializa una base demo extensa para numerosos casos y excede el límite operativo del entorno. No se declara aprobada como una sola corrida. La matriz focalizada de 87 pruebas y la navegación HTTP de cierre sí fueron completadas sin fallos funcionales.

## Integridad funcional

No se modificaron factores de emisión, fórmulas, motores de cálculo, versiones metodológicas, modelos de base de datos, migraciones ni semillas demo. Los paquetes de fuentes solo crean registros cuando el usuario los selecciona y pueden editarse antes de cargar información.
