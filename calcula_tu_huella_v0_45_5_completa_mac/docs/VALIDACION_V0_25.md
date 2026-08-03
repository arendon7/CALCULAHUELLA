# Validación técnica V0.25

Fecha de validación: 2026-08-01 UTC.

## Resultado

- 125 pruebas recolectadas.
- 125 pruebas aprobadas en lotes reproducibles.
- 87 pruebas históricas de `test_app.py` aprobadas en seis lotes.
- 30 pruebas de consolidación, metodología, sector y seguridad aprobadas.
- 8 pruebas específicas de la beta guiada y ejecución del piloto aprobadas.

## Comprobaciones adicionales

- Compilación de módulos Python sin errores.
- Sintaxis de scripts `.sh` y `.command` validada.
- `Info.plist` de la aplicación macOS validado.
- Instalación limpia mediante Alembic hasta `20260731_0015`.
- Estado de disponibilidad de instalación limpia: `ready`.
- Migración real de una base V0.24 a V0.25 comprobada.
- Cadena de auditoría posterior a la migración: íntegra.
- Inicio idempotente del piloto comprobado.
- Creación de 20 vínculos entre requisitos, fuentes y solicitudes en el piloto de prueba.
- Exportación e importación Excel comprobadas.
- Recálculo de electricidad y actualización de progreso comprobados.
- Puerta de aprobación bloqueada ante faltantes comprobada.

## Tamaño auditado

- 34 archivos Python.
- 56 plantillas HTML.
- 220 rutas HTTP detectadas.
- 18.135 líneas Python.

## Límites reconocidos

- La aplicación local no está firmada ni notarizada por Apple.
- Los factores todavía clasificados como demostrativos o piloto no son promovidos automáticamente a uso formal.
- La aprobación interna del piloto no sustituye una verificación externa.
- El despliegue productivo continúa condicionado a PostgreSQL administrado, secretos robustos, HTTPS, monitoreo, pruebas de penetración y validación metodológica independiente.
