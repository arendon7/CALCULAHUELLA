# Validación local de la migración

Fecha: 2026-08-03  
Base: `calcula_tu_huella_v0_45_5_completa_mac`

## Resultado

La base canónica v0.45.5 fue validada con la estructura de desarrollo local propuesta para el repositorio.

### Validaciones aprobadas

- Compilación de Python en `app`, `scripts`, `tests` y `run.py`.
- Sintaxis de scripts `.sh` y `.command`.
- Migraciones Alembic desde una base SQLite vacía hasta la revisión `20260803_0029`, correspondiente a v0.45.
- Compilación de **64 plantillas Jinja** usando el entorno y los filtros reales de la aplicación.
- **18 pruebas críticas aprobadas** en los módulos de marca, navegación, onboarding, primer inventario e importación guiada.
- Inicio efectivo de Uvicorn con una base limpia.
- Respuestas HTTP verificadas:
  - `/`: 200;
  - `/login`: 200;
  - `/diagnostico`: 200.

## Configuración de la prueba

- `APP_ENV=test`;
- SQLite local aislado;
- datos demo habilitados;
- navegador automático deshabilitado;
- scheduler deshabilitado;
- CSRF deshabilitado únicamente para la prueba automatizada;
- host `127.0.0.1`;
- puerto `8766`.

## Alcance

Esta validación certifica que el contenido de v0.45.5 es compatible con:

- `scripts/dev/setup.sh`;
- `scripts/dev/run.sh`;
- `scripts/dev/test.sh`;
- `.env.local.example`;
- `Makefile`;
- `docker-compose.local.yml`.

La construcción Docker no pudo ejecutarse en el entorno de validación porque Docker no está instalado allí. La sintaxis y configuración se validarán nuevamente mediante GitHub Actions cuando el árbol fuente completo quede confirmado en la rama.
