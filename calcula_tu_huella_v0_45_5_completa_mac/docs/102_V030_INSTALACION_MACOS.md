# V0.30 · ciclo de vida seguro en macOS

## Objetivo

Eliminar la dependencia de carpetas descargadas y evitar que una actualización pierda datos o deje múltiples versiones activas.

## Arquitectura

- Código activo: `~/Library/Application Support/CalculaTuHuella/current`
- Datos: `~/Library/Application Support/CalculaTuHuella/data`
- Runtime: `~/Library/Application Support/CalculaTuHuella/runtime`
- Logs: `~/Library/Application Support/CalculaTuHuella/logs`
- Respaldos: `~/Library/Application Support/CalculaTuHuella/backups`
- App: `~/Applications/Calcula tu Huella.app`

## Reglas de eliminación

El instalador no realiza búsquedas genéricas ni elimina carpetas arbitrarias. Solo procesa nombres que coinciden de forma inequívoca con versiones de Calcula tu Huella y que contienen marcadores técnicos de la plataforma (`app/`, `run.py`, `alembic.ini`).

Antes de retirar una carpeta:

1. detiene el proceso conocido;
2. identifica la base más reciente;
3. crea un archivo comprimido con `instance` y `.env` cuando existen;
4. migra la base hacia el almacenamiento persistente;
5. fusiona evidencias y reportes sin sobrescribir archivos existentes;
6. valida la versión nueva;
7. mueve la carpeta a la Papelera.

## Rollback

El código anterior se conserva temporalmente en `previous`. Si la creación del entorno, instalación de dependencias, migración o chequeo de disponibilidad falla, el instalador restaura automáticamente ese código y no ejecuta limpieza de versiones anteriores.
