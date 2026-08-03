# Validación técnica · Calcula tu Huella V0.36

## Resultado

V0.36 queda aprobada como base completa para la siguiente iteración. Conserva todos los módulos de V0.35 y amplía la arquitectura por dominios sin modificar factores, fórmulas ni resultados históricos.

## Arquitectura

- `app/organizations_web.py`: organización y sedes.
- `app/information_web.py`: solicitudes, datos, evidencias e importación.
- `app/review_web.py`: observaciones, revisión, aprobación, cierre y reapertura.
- Se conservan `users_web.py`, `inventories_web.py`, `reports_web.py` y `operations_web.py`.
- Siete dominios explícitos.
- 48 rutas únicas con propiedad de dominio.
- Cero duplicados de método y ruta.
- `main.py`: 4.348 líneas, frente a 5.454 en V0.35.

## Pruebas

Se aprobaron **200 pruebas automatizadas** en procesos aislados:

- 87 flujos históricos del núcleo;
- 108 pruebas especializadas V0.21–V0.35;
- 5 pruebas nuevas V0.36.

Las pruebas cubren inventarios, cálculos, factores, evidencia, importación, revisión, cierres, reportes, seguridad, instalación, continuidad, piloto, metodología, operación comercial y arquitectura.

## Migración real V0.35 → V0.36

La migración Alembic `20260803_0024` fue aplicada sobre una base V0.35 existente y conservó:

- 2 organizaciones;
- 3 inventarios;
- 44 registros de actividad;
- 68 cálculos.

Resultado:

- revisión Alembic: `20260803_0024`;
- integridad SQLite: `ok`;
- inventarios activos actualizados a V0.36;
- versión formal cerrada `1.0` conservada;
- sin recalculo ni alteración de resultados.

## Instalación macOS

El instalador conserva datos fuera del código, crea respaldo, ejecuta Alembic, valida salud y preparación, protege el ZIP V0.36 y retira únicamente versiones anteriores después de una actualización exitosa.

## Limitación

V0.36 sigue siendo una versión de consolidación. Antes de V1 deben dividirse `database.py` y otros dominios avanzados, cerrarse el piloto Greenatics con datos reales y validarse un despliegue productivo administrado.
