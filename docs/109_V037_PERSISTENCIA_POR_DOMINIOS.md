# V0.37 · Persistencia por dominios

## Objetivo

Reducir el acoplamiento de `database.py` sin cambiar el esquema, las rutas ni los resultados históricos.

## Arquitectura aplicada

- `app/db/base.py`: motor, sesión, metadatos y rutas persistentes.
- `app/db/models/core.py`: organización, usuarios, membresías, configuración y sedes.
- `app/db/models/operations.py`: automatizaciones, integraciones, notificaciones, auditoría y continuidad.
- `app/db/models/inventory.py`: inventarios, fuentes, datos, evidencias, revisión, reducción e informes.
- `app/db/models/supply_chain.py`: proveedores y respuestas.
- `app/db/models/methodology.py`: unidades, gases, GWP, factores, cálculos y cumplimiento.
- `app/db/models/commercial.py`: SaaS, comercial, facturación y customer success.
- `app/db/models/climate.py`: inteligencia, riesgos, transición y divulgación.
- `app/db/models/governance.py`: consolidación y validación metodológica.
- `app/db/models/pilot.py`: piloto, cargas, calidad y cierres mensuales.

`app/database.py` continúa exportando los mismos nombres para no romper módulos, migraciones ni integraciones existentes.

## Repositorios y servicios

Se implementaron repositorios con aislamiento por organización y servicios transaccionales para:

- organización y sedes;
- inventarios y límites de sedes;
- informes y aprobación.

Las rutas existentes fueron conectadas a estas capas sin cambiar URL, permisos ni formularios.

## Criterios de aceptación

- 101 modelos registrados en el mismo `Base.metadata`;
- nueve módulos de modelos importables;
- `database.py` menor a 2.200 líneas;
- cero rutas duplicadas;
- mismas 48 rutas propiedad de siete dominios web;
- migración Alembic no destructiva;
- resultados históricos sin recálculo.

## Pendientes

- ampliar repositorios y servicios a metodología, revisión, piloto y cadena de valor;
- reducir las funciones de inicialización aún concentradas en `database.py`;
- separar semillas demostrativas del arranque productivo;
- validar PostgreSQL administrado.
