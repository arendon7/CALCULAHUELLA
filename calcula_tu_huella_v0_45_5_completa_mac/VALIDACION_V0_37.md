# Validación técnica · Calcula tu Huella V0.43

## Resultado

V0.43 queda aprobada como base completa para la siguiente iteración. Conserva toda la plataforma V0.36 y divide la persistencia sin modificar tablas, factores, fórmulas, GWP ni resultados históricos.

## Arquitectura

- `database.py`: 1.963 líneas, frente a 4.210 en V0.36.
- 101 modelos ORM distribuidos en nueve módulos.
- 101 tablas registradas en el mismo `Base.metadata`.
- tres repositorios iniciales: organizaciones, inventarios e informes.
- tres servicios iniciales: organizaciones/sedes, inventarios e informes.
- siete dominios web y 48 rutas con propiedad explícita.
- cero rutas duplicadas.
- 258 rutas registradas al arrancar; 252 rutas únicas por path.
- compatibilidad pública de `app.database` conservada.

## Pruebas

Se ejecutaron 206 pruebas en procesos y lotes aislados:

- 87 pruebas históricas del núcleo en `test_app.py`;
- 113 pruebas especializadas V0.21–V0.36;
- 6 pruebas nuevas V0.43.

Todas aprobaron. El conjunto se ejecutó por lotes porque la inicialización completa de la base demostrativa excede el límite temporal de una única corrida acumulada.

## Migración real V0.36 → V0.43

Se aplicó Alembic `20260803_0025` sobre una base V0.36 existente.

Antes y después se conservaron:

- 2 organizaciones;
- 3 inventarios;
- 44 registros de actividad;
- 68 cálculos de emisiones;
- 0 artefactos de informe en la base ensayada.

Resultado:

- revisión Alembic: `20260803_0025`;
- inventarios activos actualizados a V0.43;
- inventario histórico cerrado V1.0 conservado;
- integridad SQLite: `ok`.

## Aislamiento multiorganización

Las nuevas consultas de sedes, organizaciones, inventarios e informes aplican filtros explícitos por organización. Las pruebas comprobaron que un identificador válido de otra organización no puede recuperarse mediante los repositorios.

## Instalación macOS

- ciclo de vida actualizado a V0.43;
- ZIP vigente protegido durante la limpieza;
- respaldo previo `pre_v037`;
- migración automática hasta Alembic V0.43;
- rollback y separación entre código y datos conservados;
- scripts validados con `bash -n` y pruebas del instalador en modo aislado.

## Limitaciones

V0.43 no declara preparación para SaaS público. Continúan pendientes:

- ampliar repositorios y servicios al resto de dominios;
- separar semillas y bootstrap de `database.py`;
- validar PostgreSQL administrado;
- cerrar el piloto Greenatics con datos y soportes reales;
- completar validación metodológica independiente.
