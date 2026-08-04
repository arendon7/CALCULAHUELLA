# Bandeja de importación canónica

Esta carpeta recibe temporalmente el ZIP definido en:

```text
migration/current-release.json
```

Entrega actual:

```text
calcula_tu_huella_v0_52_0_onboarding_guiado_dual_mac_windows.zip
SHA-256: 4186571c49741e86e899e9c6554e3cb78b40c2b657c5807d775d557540c85a01
```

## Estado

El checksum, el manifiesto y la validación V0.52 están recuperados y registrados. El ZIP binario no está montado todavía en el entorno activo ni presente en esta carpeta; por eso la importación no se declara ejecutada.

## Funcionamiento

Cuando aparece un ZIP en esta carpeta, `.github/workflows/import-current-release.yml`:

1. lee el nombre y SHA-256 desde `current-release.json`;
2. rechaza nombres o hashes diferentes;
3. exige las distribuciones `MAC/` y `WINDOWS/`;
4. verifica que el núcleo compartido sea idéntico;
5. rechaza bases, secretos, evidencias, certificados, logs y cachés;
6. usa `MAC/` como runtime canónico;
7. conserva diferencias Windows en `platform/windows/overlay/`;
8. aplica Alembic desde una base vacía;
9. comprueba versión, rutas, modelos y plantillas;
10. ejecuta pruebas focalizadas y Docker;
11. elimina el ZIP antes del commit automático;
12. publica el resultado mediante CI, GitHub Pages y Codespaces.

El ZIP es un insumo transitorio. Nunca permanece versionado después de una importación aprobada.

## Versiones futuras

No se crea una carpeta ni un workflow nuevo. Se actualiza `current-release.json` y se usa esta misma bandeja.
