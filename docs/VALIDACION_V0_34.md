# Validación técnica · Calcula tu Huella V0.34

## Resultado

**Aprobada para demostración, piloto controlado y continuidad local en macOS.**

No se declara todavía lista para SaaS público ni se considera cerrado el piloto Greenatics con datos reales.

## Cambios validados

- restauración aislada de respaldos SQLite;
- integridad ZIP, manifiesto, rutas seguras y archivo de base declarado;
- `PRAGMA integrity_check`;
- tablas críticas y conteos de registros;
- historial auditable de ensayos;
- vigencia productiva máxima de 90 días;
- comando macOS de doble clic;
- extracción del módulo de operación desde `main.py`;
- migración Alembic `20260802_0022`.

## Pruebas automatizadas

- **190 pruebas detectadas** en la base de código.
- **109 pruebas de regresión ejecutadas y aprobadas** en lotes controlados, incluyendo:
  - consolidación;
  - metodología;
  - piloto Greenatics;
  - seguridad;
  - calidad de datos;
  - cierre mensual;
  - biblioteca Colombia;
  - cargas operativas;
  - experiencia de producto;
  - cierre metodológico;
  - instalación macOS;
  - respaldo y restauración;
  - salud, páginas principales, cálculo y generación de respaldos.
- Los lotes se ejecutaron de forma aislada para evitar que el límite temporal de la herramienta interrumpiera una corrida monolítica prolongada.

## Migración real V0.33 → V0.34

Se migró una copia real de la base V0.33:

- organizaciones: 2 → 2;
- inventarios: 3 → 3;
- registros de actividad: 44 → 44;
- cálculos: 68 → 68;
- nueva tabla `restore_drills`: creada;
- revisión Alembic final: `20260802_0022`;
- integridad SQLite: `ok`.

## Ensayo real de restauración

Sobre una instalación limpia se creó y restauró un respaldo con:

- 102 tablas;
- 2 organizaciones;
- 5 usuarios;
- 3 inventarios;
- 16 fuentes;
- 44 registros de actividad;
- 68 cálculos;
- 2 evidencias;
- integridad: `ok`;
- todas las puertas del ensayo: aprobadas.

## Arquitectura

- `app/main.py`: 5.922 líneas.
- nuevo módulo `app/operations_web.py`: 176 líneas.
- rutas runtime: 257.
- archivos Python: 57.
- pruebas detectadas: 190.

La separación de operación constituye un avance real de `TD-001`, pero el controlador principal y `database.py` continúan requiriendo división progresiva por dominios.

## Limitaciones pendientes

- piloto Greenatics todavía requiere archivos y soportes reales completos;
- PostgreSQL y almacenamiento administrado no están implantados en el modo Mac local;
- falta monitoreo externo y restauración sobre infraestructura equivalente a producción;
- faltan revisión independiente de seguridad y validación comercial.

## Validación desde el ZIP final

- extracción limpia: aprobada;
- archivos de base, logs y temporales dentro del paquete: ninguno;
- scripts `.command` y `.sh`: sintaxis válida;
- migración desde cero hasta `20260802_0022`: aprobada;
- inicio de sesión y ventana de operación: aprobados;
- ensayo de restauración desde el paquete: aprobado;
- instalador macOS en modo de prueba: aprobado;
- recibo de instalación: versión `0.34.0`.
