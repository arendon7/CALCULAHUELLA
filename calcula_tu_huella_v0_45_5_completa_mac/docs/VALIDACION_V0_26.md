# Validación técnica V0.26

Fecha de construcción: 2026-08-01.

## Comprobaciones ejecutadas

- Compilación de `app/` y `tests/` sin errores.
- 8 pruebas específicas de V0.26 aprobadas.
- 8 pruebas de regresión V0.25 aprobadas.
- 30 pruebas de V0.21–V0.24 aprobadas en ejecuciones independientes.
- 11 pruebas representativas del núcleo histórico aprobadas.
- Instalación limpia SQLite con Alembic hasta `20260801_0016`.
- Migración real de una base V0.25 a V0.26.
- Diagnóstico `/api/ready`: estado `ready` en ambiente local.
- Sintaxis de scripts `.sh` y `.command` validada.
- `Info.plist` validado con versión `0.26.0`.

## Pruebas V0.26

- Generación de plantilla con hojas controladas.
- Validación sin modificar el inventario.
- Bloqueo de valores negativos.
- Hallazgo DQ-005 persistente.
- Prevención de archivo duplicado mediante SHA-256.
- Aplicación separada y creación de `ActivityData`.
- Página y descarga disponibles.
- Cliente con consulta, sin permiso para cargar.

## Alcance

Las pruebas verifican la aplicación local y la migración SQLite. No constituyen prueba de penetración, validación metodológica externa ni ensayo de carga productiva.
