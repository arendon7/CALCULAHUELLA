# V1.6 · Data Surfaces · Sectorization

## Estado previo

Captura (`capture_web.py`), información (`information_web.py`) e importaciones operativas (`operational_imports_web.py`) ya tenían autoridad propia. La superficie de datos que permanecía embebida en `main.py` era sectorización.

## Corte materializado

- `GET /sectorizacion` y `POST /sectorizacion/aplicar` pasan a `app/sectorization_web.py`.
- `main.py` conserva únicamente el registro del módulo.
- Se preservan selección de plantilla, deduplicación de fuentes, selección de sede, asignación automática de versiones de factor aprobadas, actualización de progreso y auditoría.

## Contratos

1. Exactamente dos rutas de sectorización, sin duplicados.
2. La pantalla sigue disponible.
3. Aplicar una plantilla crea fuentes cuando corresponde.
4. Reaplicar la misma plantilla no duplica fuentes.
5. No se modifica lógica de cálculo, factores, GWP ni migraciones.
