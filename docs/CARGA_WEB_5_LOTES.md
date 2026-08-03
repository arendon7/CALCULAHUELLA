# Carga web normal en cinco lotes

La rama de recepción es `migration/v0.45.5-complete`.

La fuente canónica se dividió en cinco lotes, cada uno con menos de 100 archivos y conservando las rutas reales del repositorio:

| Lote | Contenido | Archivos |
|---|---|---:|
| 01 | `app/templates` y `app/static` | 73 |
| 02 | resto del núcleo `app` | 82 |
| 03 | `docs`, `ops` e `instance/.gitkeep` | 86 |
| 04 | `migrations`, `tests` y `scripts` | 79 |
| 05 | archivos raíz, configuración, empaquetado y `.github` | 72 |

## Procedimiento

1. Seleccionar la rama `migration/v0.45.5-complete`.
2. Abrir **Add file → Upload files**.
3. Abrir la carpeta del lote en Finder.
4. Arrastrar **el contenido del lote**, no la carpeta `LOTE_*`.
5. Confirmar que las rutas comiencen por `app/`, `docs/`, `migrations/`, etc.; nunca por `LOTE_*`.
6. Confirmar la carga y repetir en orden del 01 al 05.

Para ver los archivos ocultos del lote 05 en Finder, usar `Command + Shift + .`.

## Mensajes de commit

- Lote 01: `feat: importar plantillas y recursos visuales v0.45.5`
- Lote 02: `feat: importar núcleo de aplicación v0.45.5`
- Lote 03: `docs: importar documentación y operación v0.45.5`
- Lote 04: `test: importar migraciones pruebas y scripts v0.45.5`
- Lote 05: `chore: completar archivos raíz y empaquetado v0.45.5`

Al finalizar, el árbol será comparado contra el manifiesto y se ejecutará CI antes de fusionar a `main`.
