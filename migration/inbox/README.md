# Bandeja de importación V0.48.0

Esta carpeta recibe temporalmente el archivo autocontenido exacto:

```text
calcula_tu_huella_v0_48_0_portafolio_reduccion_mac.zip
```

SHA-256 obligatorio:

```text
921a97f8cf6a74c60161c9e96afcaed13c713afebdf09dedc8309c77a961b5d3
```

## Procedimiento web

1. Abrir esta carpeta en la rama `migration/v0.48.0-canonical`.
2. Seleccionar **Add file → Upload files**.
3. Cargar el ZIP con el nombre exacto.
4. Confirmar el commit sobre la misma rama.

GitHub Actions ejecutará `.github/workflows/import-v048.yml` y:

- verificará el SHA-256 del ZIP;
- comprobará versión, manifiesto, plantillas, pruebas, logos e imágenes;
- rechazará bases, secretos, evidencias, logs o cachés;
- reemplazará la fuente anterior conservando `.github`, `.devcontainer` y las herramientas de migración;
- aplicará Alembic desde una base vacía;
- comprobará 284 rutas, 109 modelos y 65 plantillas;
- ejecutará pruebas focalizadas V0.46–V0.48 y seguridad;
- construirá la imagen Docker;
- eliminará el ZIP del repositorio;
- confirmará el árbol V0.48.0 ya descomprimido.

El archivo comprimido es un insumo transitorio y no permanecerá versionado después de la importación.
