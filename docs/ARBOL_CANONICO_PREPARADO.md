# Árbol canónico preparado

Fecha: 2026-08-03

La fuente v0.45.5 fue descomprimida, reconciliada y preparada como repositorio ejecutable.

## Contenido preparado

- 392 archivos versionables.
- 3.086.716 bytes.
- SHA-256 lógico del árbol ordenado: `407a3945b91ae0de96628373f7aeed41e7c979c98d0f12e8ab73266b7d6cdb09`.
- Cuatro láminas PNG conservadas con compresión sin pérdida y píxeles idénticos.
- Scripts `.sh`, `.command` y lanzador macOS marcados como ejecutables.
- Manifiesto de entrega, bases, cachés, logs, secretos y datos operativos excluidos.

## Componentes incorporados al árbol preparado

- aplicación FastAPI completa;
- 64 plantillas Jinja;
- recursos CSS, JavaScript, SVG y PNG;
- migraciones Alembic;
- pruebas automatizadas;
- documentación histórica y vigente;
- Docker, Caddy y operación;
- instaladores y lanzadores macOS;
- `scripts/dev/setup.sh`, `run.sh` y `test.sh`;
- `.env.local.example`;
- `docker-compose.local.yml`;
- `Makefile`;
- GitHub Actions;
- documentación de desarrollo local.

## Validación previa

- Compilación Python correcta.
- Sintaxis de scripts correcta.
- Migraciones Alembic ejecutadas desde una base limpia hasta `20260803_0029`.
- 64 plantillas compiladas con el entorno real de la aplicación.
- Pruebas v0.45, v0.45.1, v0.45.2 y v0.45.3 aprobadas.
- La prueba v0.45.4 conserva un caso heredado de ejecución prolongada que requiere aislamiento en CI.

## Estado de transferencia

El árbol está preparado en el entorno de trabajo, pero el conector de GitHub expuesto en este chat no admite un archivo local como entrada binaria para `create_blob`. La API recibe únicamente contenido UTF-8/base64 ya materializado en la llamada. Por ello no se declara importado hasta que GitHub contenga y verifique los 392 archivos.
