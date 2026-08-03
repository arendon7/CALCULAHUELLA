# Validación técnica V0.33

## Resultado

V0.33 queda aprobada para demostración y ejecución controlada del piloto Greenatics en macOS. No se declara cerrado el inventario real ni lista para SaaS público.

## Pruebas

- 184 pruebas automatizadas aprobadas en lotes aislados.
- 8 pruebas específicas V0.33.
- Rutas históricas, cálculos, metodología, cierres, importaciones, seguridad, operación y experiencia conservados.

## Migración real V0.32 → V0.33

Base evaluada antes y después:

- 2 organizaciones conservadas.
- 3 inventarios conservados.
- 44 registros de actividad conservados.
- 68 cálculos conservados.
- revisión Alembic final: `20260802_0021`.
- integridad SQLite: `ok`.

La tabla `pilot_source_comparisons` se crea vacía y se llena únicamente cuando se inicia o consulta una ejecución del piloto; no fabrica resultados independientes.

## Funcionalidad validada

- creación idempotente del piloto;
- tablero por sede;
- cobertura mensual basada en periodos reales;
- control de evidencia y frecuencia;
- exportación de plantilla ampliada;
- importación de contraste por fuente;
- cálculo de variación y conformidad;
- auditoría de revisiones;
- bloqueo de aprobación incompleta;
- interfaz web y permisos por rol.

## Limitación de datos

Los datos operativos parciales conocidos se muestran como contexto, no como registros calculables. Para cerrar el piloto se requieren archivos mensuales y evidencias reales de Yarumal, Támesis y operación corporativa.
