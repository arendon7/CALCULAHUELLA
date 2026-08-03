# Validación técnica · Calcula tu Huella V0.35

## Resultado

V0.35 queda aprobada como base completa para la siguiente iteración. La versión conserva todos los módulos de V0.34 y separa progresivamente el controlador principal por dominios.

## Cobertura automatizada

- 195 pruebas recolectadas y aprobadas en lotes independientes.
- 87 pruebas del núcleo histórico V0.1–V0.20.
- 108 pruebas de consolidación V0.21–V0.35.
- 258 rutas registradas.
- 24 rutas con propiedad explícita en módulos de dominio.
- cero duplicados de método + ruta.

## Arquitectura

| Dominio | Archivo | Rutas |
|---|---|---:|
| Usuarios y membresías | `app/users_web.py` | 4 |
| Inventarios y fuentes | `app/inventories_web.py` | 11 |
| Informes y artefactos | `app/reports_web.py` | 4 |
| Operación y continuidad | `app/operations_web.py` | 5 |

`app/main.py` pasó de 5.922 a 5.454 líneas. La paridad se valida mediante `app/architecture.py` y el endpoint autenticado `/api/arquitectura/resumen`.

## Migración real V0.34 → V0.35

Se migró una copia de una base V0.34 existente:

- organizaciones: 2 → 2;
- inventarios: 3 → 3;
- datos de actividad: 44 → 44;
- cálculos: 68 → 68;
- revisión Alembic: `20260802_0022` → `20260803_0023`;
- integridad SQLite: `ok`.

Los inventarios históricos conservaron sus resultados. Los inventarios activos anteriores quedaron identificados como V0.35; las versiones formales cerradas se conservaron.

## Instalador macOS

Se validó en un HOME aislado:

- copia de la aplicación a una ubicación estable;
- recibo de instalación `0.35.0`;
- creación de la aplicación y del acceso del Escritorio;
- preservación del ZIP V0.35;
- traslado a la Papelera de carpetas y ZIP V0.34;
- migración limpia hasta Alembic `20260803_0023`;
- base inicial con integridad `ok`;
- 258 rutas y paridad de dominios correcta.

Se corrigió un defecto heredado del limpiador: protegía el identificador V0.32 en lugar de la versión vigente. Ahora usa `CTH_RELEASE_SLUG="v0_35"`.

## Metodología

V0.35 no cambia factores, fórmulas, GWP, incertidumbre, reglas de consolidación ni tratamiento contable. Las pruebas históricas confirmaron que los resultados y flujos permanecen compatibles.

## Pendientes

- separar organización y sedes;
- separar información, evidencias y revisión;
- reducir responsabilidades de `database.py`;
- ejecutar el piloto Greenatics con datos reales completos;
- validar infraestructura productiva administrada.
