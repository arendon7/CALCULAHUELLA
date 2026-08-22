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
- PostgreSQL **17** administrado y aislado para los datos transaccionales del preview;
- seed demo para poder recorrer roles y journeys;
- health check en `/api/health`;
- autodespliegue **solo cuando los checks de CI del commit pasan**.

URL prevista del servicio: `https://calcula-tu-huella-arendon7-preview.onrender.com`.

> Este entorno es de preview/UAT, no producción. El plan Free de Render Postgres expira 30 días después de su creación y no incluye backups; debe tratarse como una base temporal de ensayo. Los archivos subidos usan además almacenamiento local efímero y pueden perderse al reiniciar, redesplegar o dormir el web service. `DEPLOYMENT_STRICT=false` y `SCHEDULER_ENABLED=false` se mantienen deliberadamente en staging. La base Supabase real no se utiliza para esta UAT aislada.

La web pública permanece en `site/`. Su botón **Iniciar sesión** está preparado para enlazar con el servicio web anterior cuando el Blueprint esté activo y certificado. GitHub Pages continúa protegido para publicación desde `main`; el staging completo no requiere modificar esa protección.

Una vez aprovisionado el host, ejecuta el workflow manual `V2.1 · Remote staging live gate` contra su URL HTTPS. El gate es no destructivo: valida health, login, diagnóstico, privacidad y defensas CSRF/contacto sin crear leads ni modificar datos de negocio.

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
- `migrations/`: esquema Alembic reconciliado hasta `20260812_0040`.
- `tests/`: batería funcional y metodológica.
- `scripts/`: certificación, respaldo, restauración y operación.
- `deployment/`, `Dockerfile`, `docker-compose*.yml`: despliegue completo.
- `render.yaml`: staging online aislado y pinneado a PostgreSQL 17.
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