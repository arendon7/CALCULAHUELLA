# Validación técnica V0.32

Fecha de cierre: 2026-08-02.

## Resultado

V0.32 queda aprobada para demostración y piloto controlado local en macOS. No se declara lista para despliegue SaaS público.

## Pruebas

- 87 pruebas del núcleo histórico `test_app.py`: aprobadas en lotes aislados.
- 89 pruebas de consolidación V0.21–V0.32: aprobadas por módulo.
- Total: 176 pruebas aprobadas.
- 10 pruebas específicas V0.32.
- Compilación Python de `app`, `migrations` y `scripts`: aprobada.
- Salud: HTTP 200, versión `0.32.0`.
- Rutas FastAPI registradas: 254.

La ejecución monolítica de toda la batería heredada puede prolongar el cierre del proceso de pytest; por eso la validación se realizó en lotes deterministas. No se observaron fallos funcionales en los lotes.

## Migración real V0.31 → V0.32

- 2 organizaciones conservadas.
- 3 inventarios conservados.
- 44 registros de actividad conservados.
- 68 cálculos migrados y completados con campos de incertidumbre.
- Integridad SQLite: `ok`.
- Revisión Alembic final: `20260802_0020`.

## Cierre metodológico

Aprobado:

- tratamiento separado de emisiones brutas, CO2 biogénico, remociones, evitadas y compensaciones;
- clasificación de alcance 2;
- política y evaluación de recalculo del año base;
- incertidumbre del dato y del factor;
- propagación por raíz de suma de cuadrados;
- cobertura explícita de incertidumbre;
- bloqueo de cambios de clasificación en inventarios cerrados;
- auditoría y revisión humana.

## Reportes

- Informe ejecutivo PDF generado y renderizado: 2 páginas, sin recortes visibles.
- Informe técnico PDF generado y renderizado: 7 páginas, sin recortes visibles.
- Memoria XLSX generada y abierta; incluye hoja `Cierre metodológico`, partida e incertidumbre por cálculo.
- El rango de incertidumbre se identifica como parcial cuando no cubre todo el inventario.

## Instalación macOS

- Instalador por doble clic: aprobado en modo de prueba.
- Actualización, respaldo, acceso en Aplicaciones, acceso de Escritorio y limpieza de versiones anteriores: aprobados.
- Reconocimiento de bases V0.22–V0.32 sin tabla Alembic: actualizado.
- Datos persistentes separados del código.

## Límites de salida

Para producción pública aún se requieren PostgreSQL, HTTPS, secreto externo, almacenamiento administrado, correo transaccional, observabilidad, análisis de archivos, pruebas de carga y revisión independiente de seguridad y metodología.
