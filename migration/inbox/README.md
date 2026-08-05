# Bandeja de importación canónica

Esta carpeta recibe temporalmente el ZIP definido en:

```text
migration/current-release.json
```

Entrega actual:

```text
calcula_tu_huella_v1_0_0_rc1_dual_mac_windows.zip
SHA-256: 31847280ea71ff9bfa4c6c6150eacee45fc782f3fbfdd20155e3b94e2b394742
```

## Estado

La entrega **V1.0.0-RC1** está aprobada internamente como candidata para pilotos y aceptación controlada. No está autorizada como V1.0 productiva.

Están recuperados y registrados:

- checksum exacto del ZIP;
- manifiesto del paquete;
- validación técnica;
- documento de estabilización y lanzamiento;
- conteos de rutas, modelos, tablas y plantillas;
- árboles SHA-256 de Mac y Windows;
- SHA-256 de la evidencia automatizada.

El ZIP binario no está montado todavía en el entorno activo ni presente en esta carpeta. Por eso la importación no se declara ejecutada.

## Contrato RC1

```text
Runtime: 1.0.0-rc1
Rutas: 315
Modelos ORM: 112
Tablas físicas: 113
Plantillas HTML: 75
Alembic: 20260805_0032
Archivos de prueba: 41
Pruebas aprobadas documentadas: 331
```

## Funcionamiento

Cuando aparece el ZIP exacto, `.github/workflows/import-current-release.yml`:

1. lee nombre y SHA-256 desde `current-release.json`;
2. rechaza nombres o hashes diferentes;
3. exige `MAC/`, `WINDOWS/` y los tres documentos de gobierno RC1;
4. verifica el núcleo compartido y la evidencia automatizada;
5. exige los cuatro activos oficiales de marca;
6. rechaza bases, secretos, evidencias operativas, certificados privados, logs y cachés;
7. usa `MAC/` como runtime canónico;
8. conserva diferencias Windows en `platform/windows/overlay/`;
9. aplica Alembic desde una base vacía;
10. comprueba versión, 315 rutas, 112 modelos, 113 tablas y 75 plantillas;
11. ejecuta los 41 archivos de pruebas en procesos aislados;
12. construye Docker;
13. elimina el ZIP antes del commit automático;
14. publica el resultado mediante CI, GitHub Pages y Codespaces.

La importación mantiene siempre:

```text
production_authorized = false
```

Importar RC1 no aprueba pilotos, Windows 10/11, seguridad independiente, documentos jurídicos ni infraestructura productiva real.

## Versiones futuras

No se crea otra carpeta ni otro workflow. Se actualiza `current-release.json` y se utiliza esta misma bandeja.
