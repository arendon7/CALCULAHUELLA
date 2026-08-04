# Bandeja de importación V0.49.0

Esta carpeta recibe temporalmente el paquete dual exacto:

```text
calcula_tu_huella_v0_49_0_dual_mac_windows.zip
```

SHA-256 obligatorio:

```text
b83066b35490bfed325ee2d74cf38cfeb14c216c0a63632c19140a777f763c06
```

## Estado

El manifiesto, la validación y el checksum están recuperados en la Biblioteca del proyecto. El ZIP binario no está montado en el entorno activo ni presente todavía en esta carpeta. Por tanto, la importación no se declara ejecutada.

## Procedimiento web

1. Abrir esta carpeta en la rama `migration/v0.49.0-canonical`.
2. Seleccionar **Add file → Upload files**.
3. Cargar el ZIP con el nombre exacto.
4. Confirmar el commit sobre la misma rama.

GitHub Actions ejecutará `.github/workflows/import-v049.yml` y:

- verificará el SHA-256 exacto;
- comprobará las distribuciones `MAC/` y `WINDOWS/`;
- verificará que el núcleo compartido sea idéntico;
- exigirá versión 0.49.0, landing, selección dato–factor, logos e imágenes modulares;
- rechazará bases, secretos, evidencias, certificados, logs y cachés;
- usará `MAC/` como runtime canónico por ser la distribución ejecutada en validación;
- conservará las diferencias de Windows en `platform/windows/overlay/`;
- aplicará Alembic desde una base vacía hasta `20260804_0030`;
- comprobará 287 rutas, 110 modelos y 65 plantillas;
- ejecutará pruebas V0.46–V0.49 y seguridad;
- construirá Docker;
- eliminará el ZIP del repositorio;
- confirmará el árbol V0.49.0 ya descomprimido.

El ZIP es un insumo transitorio y no permanecerá versionado después de la importación.
