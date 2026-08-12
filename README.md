# Calcula tu Huella · V1.0.0 canónica

Esta es la **fuente canónica única** de Calcula tu Huella. Consolida la aplicación completa, las migraciones, pruebas, despliegue, instaladores locales, documentación vigente y una vista previa estática para GitHub Pages.

## Estado

- Aplicación completa: FastAPI + Jinja + SQLAlchemy + Alembic.
- Uso local: macOS y Windows mediante instaladores incluidos.
- Despliegue completo: contenedor con PostgreSQL y almacenamiento externo.
- GitHub Pages: vista previa estática ubicada en `site/`; no ejecuta Python, base de datos, autenticación ni cálculos persistentes.
- Versión funcional: `1.0.0`.
- Corte canónico: `2026-08-05`.

## Vista previa web V2.1.5 desde GitHub

La línea activa `feature/v2-1-0-brand-provenance` incluye `render.yaml` para levantar una instancia de **staging** directamente desde este repositorio, sin instalar Python, Homebrew, Docker ni dependencias en el computador del usuario.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https%3A%2F%2Fgithub.com%2Farendon7%2FCALCULAHUELLA%2Ftree%2Ffeature%2Fv2-1-0-brand-provenance)

El Blueprint crea:

- la aplicación FastAPI desde el `Dockerfile` del repo;
- PostgreSQL administrado para los datos transaccionales del preview;
- seed demo para poder recorrer roles y journeys;
- health check en `/api/health`;
- autodespliegue **solo cuando los checks de CI del commit pasan**.

URL prevista del servicio: `https://calcula-tu-huella-arendon7-preview.onrender.com`.

> Este entorno es de preview/UAT, no producción. Los datos transaccionales viven en PostgreSQL, pero los archivos subidos usan almacenamiento local efímero hasta conectar el backend S3/Supabase Storage. `DEPLOYMENT_STRICT=false` se mantiene deliberadamente en staging.

La web pública permanece en `site/`. Su botón **Iniciar sesión** está preparado para enlazar con el servicio web anterior cuando el Blueprint esté activo. GitHub Pages continúa protegido para publicación desde `main`; el staging completo no requiere modificar esa protección.

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
- `render.yaml`: staging online conectado al branch activo.
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
