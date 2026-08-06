# Calcula tu Huella · V1.0.0 canónica

Esta es la **fuente canónica única** de Calcula tu Huella. Consolida la aplicación completa, las migraciones, pruebas, despliegue, instaladores locales, documentación vigente y una vista previa estática para GitHub Pages.

## Estado

- Aplicación completa: FastAPI + Jinja + SQLAlchemy + Alembic.
- Uso local: macOS y Windows mediante instaladores incluidos.
- Despliegue completo: contenedor con PostgreSQL y almacenamiento externo.
- GitHub Pages: vista previa estática ubicada en `site/`; no ejecuta Python, base de datos, autenticación ni cálculos persistentes.
- Versión funcional: `1.0.0`.
- Corte canónico: `2026-08-05`.

## Inicio local

### macOS

1. Ejecuta `1_INSTALAR_Y_ABRIR.command`.
2. Para volver a abrir: `2_ABRIR_CALCULA_TU_HUELLA.command`.
3. Validación: `18_VALIDAR_VERSION_FINAL_V1.command`.

### Windows

1. Ejecuta `1_INSTALAR_Y_ABRIR.bat`.
2. Para volver a abrir: `2_ABRIR_CALCULA_TU_HUELLA.bat`.
3. Validación: `5_VALIDAR_VERSION_FINAL_V1.bat`.

## Desarrollo

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python scripts/run_test_tier.py smoke
APP_ENV=local SEED_DEMO=true python run.py
```

## Estructura

- `app/`: aplicación y motor ambiental.
- `migrations/`: esquema Alembic hasta `20260805_0036`.
- `tests/`: batería funcional y metodológica.
- `scripts/`: certificación, respaldo, restauración y operación.
- `deployment/`, `Dockerfile`, `docker-compose*.yml`: despliegue completo.
- `site/`: vista previa estática publicable en GitHub Pages.
- `docs/`: auditorías, aprobaciones, evidencia y guías.
- `.github/workflows/`: CI y publicación de Pages.

## Repositorio objetivo

La migración posterior está preparada para `arendon7/CALCULAHUELLA`. Debe realizarse mediante una rama de respaldo y un reemplazo controlado del árbol, nunca borrando `main` sin conservar el commit anterior. Consulta `docs/migracion/REEMPLAZO_REPOSITORIO_GITHUB.md`.

## Integridad

Ejecuta:

```bash
python tools/verify_canonical.py
```

El archivo `MANIFIESTO_SHA256_CANONICO.txt` contiene la huella individual de cada archivo del paquete.
