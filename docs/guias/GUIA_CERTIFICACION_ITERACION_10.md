# Guía de certificación local · Iteración 10

## macOS

1. Instale la aplicación con `1_INSTALAR_Y_ABRIR.command`.
2. Cierre la aplicación antes de una restauración real.
3. Ejecute `19_CERTIFICAR_INSTALACION.command`.
4. Revise `release/platform_preflight.json` y `instance/certifications/acceptance`.
5. Para la regresión completa: `python3 scripts/run_test_tier.py full --durations 0`.

## Windows

1. Instale la aplicación con `1_INSTALAR_Y_ABRIR.bat`.
2. Cierre la aplicación antes de una restauración real.
3. Ejecute `6_CERTIFICAR_INSTALACION.bat`.
4. Revise `release\platform_preflight.json` y `instance\certifications\acceptance`.
5. Para la regresión completa: `python scripts\run_test_tier.py full --durations 0`.

## Restauración SQLite

Validación sin modificar:

`python scripts/restore_sqlite.py RUTA_DEL_RESPALDO.zip --dry-run`

Restauración confirmada con respaldo preventivo:

`python scripts/restore_sqlite.py RUTA_DEL_RESPALDO.zip --confirm`

La aplicación debe estar detenida. No use `--skip-safety-backup` salvo que exista otro respaldo verificado.
