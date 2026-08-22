# Vercel staging · Calcula tu Huella V2.1

## Propósito

Este adaptador existe únicamente para UAT web del branch `feature/v2-1-0-brand-provenance`. No sustituye la topología productiva, el paquete Mac ni el arranque Docker/Render.

## Entry point

- `api/index.py` exporta `app` desde `app.main`.
- `vercel.json` reescribe el tráfico hacia ese entrypoint.
- Todo almacenamiento local del runtime queda bajo `/tmp/calcula-tu-huella`.
- Scheduler, email y `DEPLOYMENT_STRICT` permanecen desactivados en staging serverless.

## Persistencia

### Con `DATABASE_URL`

El runtime utiliza PostgreSQL mediante la configuración existente de la aplicación. La credencial debe inyectarse como variable de entorno del proveedor de hosting. Nunca se versiona en Git.

La base actualmente identificada para Calcula tu Huella es el proyecto Supabase activo que ya contiene el esquema y datos del producto. Antes de conectar un host público deben verificarse conectividad TLS, versión de Alembic y un backup/restauración válido.

### Sin `DATABASE_URL`

El adapter cae explícitamente a SQLite bajo `/tmp`. Este modo sirve únicamente para comprobar navegación y UX. Los datos pueden desaparecer entre invocaciones/cold starts y no deben tratarse como evidencia ni persistencia real.

## Variables mínimas para staging persistente

- `APP_ENV=staging`
- `DATABASE_URL=<secret gestionado por el hosting>`
- `SESSION_SECRET=<aleatorio, >=32 caracteres>`
- `SESSION_HTTPS_ONLY=true`
- `TRUSTED_HOSTS=<host verificado>`
- `PUBLIC_BASE_URL=https://<host verificado>`
- `SEED_DEMO=true` solo mientras el staging use datos demostrativos
- `STORAGE_BACKEND=local` mientras uploads sean únicamente UAT efímero
- `EMAIL_BACKEND=disabled`
- `SCHEDULER_ENABLED=false`
- `DEPLOYMENT_STRICT=false`
- `STRUCTURED_LOGGING=true`

## Gates antes de conectar GitHub Pages

No configurar `site/config.js -> appBaseUrl` hasta que todos sean verdaderos:

1. `GET /api/health` responde 200 por HTTPS.
2. `GET /` carga la landing FastAPI con assets estáticos.
3. `GET /diagnostico` carga sin error.
4. `GET /login` carga sin error.
5. Un login demo válido abre `/dashboard` y mantiene sesión entre requests normales.
6. `POST /contacto` crea un `CommercialLead` en PostgreSQL cuando se acepta privacidad.
7. El host configurado está incluido en `TRUSTED_HOSTS` y `PUBLIC_BASE_URL` coincide exactamente.
8. No hay secretos en Git, HTML, JavaScript o logs públicos.
9. El CI del branch permanece verde.
10. El cambio de Pages sigue limitado a `site/**`.

## Truth locks

Este adapter no autoriza cambios en factores, GWP, fórmulas, metodología, cálculos, modelos de dominio, permisos, migraciones ni semántica contable de carbono.
