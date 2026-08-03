# Validación técnica V0.22

Fecha de validación: 2026-08-01 UTC.

## Resultado

**104 pruebas aprobadas en lotes reproducibles:**

- 87 pruebas históricas de la aplicación.
- 8 pruebas de consolidación V0.21.
- 9 pruebas específicas del núcleo metodológico V0.22.

La ejecución monolítica de toda la suite excede el límite temporal del entorno de construcción; por ello se ejecutó en cinco lotes aislados. Todos los nodos de prueba recolectados fueron ejecutados y aprobados.

## Pruebas V0.22

- Inicialización de documentos fuente y casos patrón.
- Valor, unidad y trazabilidad del factor UPME.
- GWP AR6 y distinción del origen del metano.
- Aprobación de los ocho casos patrón.
- Acceso web y API por rol.
- Ejecución manual de validaciones.
- Revisión documental de factores.
- Exportación Excel.
- Priorización del factor formal sobre el demostrativo.

## Validaciones adicionales

- Compilación de módulos Python: aprobada.
- Migración Alembic `20260731_0012`: aprobada.
- Instalación limpia SQLite: aprobada.
- Estado de disponibilidad: `ready`.
- Migración V0.21 → V0.22: aprobada.
- Exportación Excel: aprobada.
- Auditoría estática: 208 rutas, 54 plantillas y 104 pruebas detectadas.
- Integridad ZIP: aprobada.

## Limitación declarada

La aprobación de pruebas confirma comportamiento del software y resultados de casos conocidos. No certifica la totalidad de la biblioteca, la idoneidad de un factor para cualquier organización ni conformidad integral con un estándar.
