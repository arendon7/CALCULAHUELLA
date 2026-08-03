# Base canónica v0.45.5

## Resultado de reconciliación

Se compararon los árboles completos de:

- v0.45.2;
- v0.45.3;
- v0.45.4;
- v0.45.5.

La v0.45.5 contiene todos los archivos funcionales presentes en las tres versiones anteriores. Los únicos elementos anteriores ausentes son cachés de pruebas, bytecode Python o manifiestos específicos de cada entrega.

Por esta razón:

- v0.45.5 será la única base fuente de la migración;
- no se mezclarán carpetas de versiones;
- las validaciones anteriores se conservarán como historial;
- un archivo anterior solo podrá recuperarse con justificación y prueba de regresión.

## Inventario inicial

Fuente analizada: `calcula_tu_huella_v0_45_5_completa_mac`

- Archivos totales: **376**
- Tamaño total: **7.670.598 bytes**
- Huella SHA-256 del árbol ordenado: `9c94ec51954345404085bd643da805951e94c0a9dea20cb8288fd25ec86af4b2`

Clasificación inicial:

| Decisión | Archivos |
|---|---:|
| Versionar en su ubicación inicial | 261 |
| Versionar como documentación | 89 |
| Reorganizar como scripts macOS | 23 |
| Reorganizar como empaquetado macOS | 2 |
| Archivar fuera del árbol Git | 1 |

La clasificación se genera con `scripts/migration/build_source_inventory.py` y deberá repetirse antes y después de la importación.

## Datos y persistencia

Los datos de producto y referencia incorporados en código, migraciones o fixtures controlados sí forman parte del repositorio.

No se confirmarán:

- bases SQLite locales;
- contenido operativo de `instance/`;
- usuarios, organizaciones o inventarios reales;
- evidencias y documentos generados;
- respaldos;
- secretos o `.env`;
- logs y cachés.

La persistencia local existente en macOS se conserva fuera del repositorio, en `~/Library/Application Support/CalculaTuHuella`.

## Verificación posterior a la importación

La importación deberá reproducir:

- los 376 archivos fuente clasificados;
- la misma huella por cada archivo versionado;
- recursos visuales intactos;
- permisos ejecutables en scripts;
- rutas, plantillas, migraciones y pruebas de v0.45.5;
- ausencia de archivos excluidos.
