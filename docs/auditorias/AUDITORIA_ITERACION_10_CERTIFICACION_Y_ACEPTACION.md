# Auditoría Iteración 10 · certificación, multiempresa y continuidad

## 1. Objetivo

Cerrar la etapa de estabilización de la versión autocontenida mediante pruebas reproducibles, recorridos reales por varias empresas, control de aislamiento organizacional, carga concurrente, respaldo/restauración y validación cruzada de los paquetes Mac y Windows.

## 2. Mejoras implementadas

### Integridad multiempresa

- Auditor automático de relaciones con `organization_id`.
- Verificación de llaves foráneas que deben permanecer dentro de la misma empresa.
- Recorridos autenticados sobre tres organizaciones accesibles.
- Prueba expresa de rechazo al intentar activar una empresa sin membresía.
- Validación de 94 controles de integridad sin hallazgos críticos.

### Cadena de auditoría concurrente

- Serialización por organización en SQLite durante la transacción.
- Bloqueo asesor transaccional en PostgreSQL.
- Prevención de bifurcaciones de hash durante sesiones concurrentes.
- Verificación de la cadena antes y después de restaurar respaldos.

### Respaldo y restauración

- Eliminación de extracción ZIP indiscriminada.
- Validación previa del manifiesto, firma, versión, integridad SQLite y cargas permitidas.
- Respaldo preventivo antes de restaurar, salvo decisión explícita.
- Reemplazo atómico de la base de datos.
- Ensayo real: se alteró un dato, se restauró el respaldo y se recuperó correctamente el valor original.

### Pruebas reproducibles

- Ejecución aislada de pytest para evitar plugins globales y retrasos de cierre del intérprete.
- Runtime y base temporal independientes.
- Validador estructural desacoplado de la base abierta por la suite.
- Comandos de certificación incluidos para Mac y Windows.

## 3. Resultados

### Mac

- 392 pruebas recopiladas.
- 392 aprobadas.
- 0 omitidas.
- Duración de referencia: 30,62 segundos en el entorno disponible.

### Windows

- 392 pruebas recopiladas desde la copia Windows.
- 389 aprobadas.
- 3 omitidas por corresponder exclusivamente al instalador macOS.
- Código funcional, pruebas y migraciones equivalentes a Mac.

### Migraciones

- Base creada desde cero en ambas copias.
- Revisión final: `20260805_0036`.
- 121 tablas, incluida la tabla de control Alembic.

### Aceptación multiempresa y carga

- 3 organizaciones recorridas.
- 27 recorridos funcionales autenticados.
- Cambio no autorizado de empresa bloqueado.
- 32 solicitudes concurrentes.
- 0 errores HTTP.
- p95 concurrente: 396,12 ms.
- Rendimiento local observado: 30,12 solicitudes por segundo.

### Regresión ambiental

La Iteración 10 no modifica factores, GWP ni fórmulas ambientales:

- 200 cálculos idénticos a la Iteración 9.
- 25 fuentes idénticas.
- 4 inventarios idénticos.
- Hash canónico: `b0cb29d2bb898b47fd6e666f1c1bfd307bf41ed1ceee3bf4d4c5110c8678243d`.

## 4. Clasificación de liberación

**Aprobada para despliegue controlado**, demostraciones, pilotos acompañados, inventarios internos y proyectos privados con supervisión profesional.

No debe comunicarse todavía como producción pública certificada, servicio infalible ni plataforma verificada independientemente.

## 5. Pendientes externos reales

1. Instalación física documentada en un Mac externo.
2. Instalación física documentada en Windows 10 y Windows 11.
3. Prueba distribuida con red, proxy, TLS y almacenamiento externo.
4. PostgreSQL productivo y restauración sobre infraestructura real.
5. Pentest independiente y cierre formal de hallazgos.
6. Validación del inventario de cada cliente por el profesional o verificador aplicable.

## 6. Archivos de evidencia

- `EVIDENCIA_CERTIFICACION_ITERACION_10.json`.
- `MAC/release/ITERACION_10_ACCEPTANCE_EVIDENCE.json`.
- `WINDOWS/release/ITERACION_10_ACCEPTANCE_EVIDENCE.json`.
- `MAC/release/platform_preflight.json`.
- `WINDOWS/release/platform_preflight.json`.

## 7. Conclusión

La versión alcanza un cierre técnico sólido para uso controlado. La deuda restante ya no corresponde principalmente al código autocontenido, sino a pruebas físicas, infraestructura productiva y aseguramiento externo.
