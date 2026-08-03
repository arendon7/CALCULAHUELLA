# Validación técnica — Calcula tu Huella V0.29 completa

Fecha de cierre: 2026-08-02  
Base canónica: `calcula_tu_huella_v0_28_mac(1).zip`

## 1. Alcance de la iteración

La V0.29 fue construida directamente sobre la plataforma V0.28 completa. No se eliminó ni sustituyó ningún módulo funcional existente.

Se añadió el módulo **Cargas operativas configurables**, integrado con:

- organizaciones, usuarios, roles y permisos;
- inventarios y periodos cerrados;
- instalaciones, fuentes y datos de actividad;
- evidencias y calidad de datos;
- recálculo de emisiones;
- auditoría y trazabilidad;
- migraciones Alembic y operación macOS.

## 2. Funcionalidad validada

- Carga de archivos CSV y XLSX.
- Detección de delimitador y hojas de cálculo.
- Previsualización antes de modificar el inventario.
- Mapeo configurable de columnas.
- Perfiles reutilizables de importación.
- Validación de fuente, instalación, fecha, valor, unidad y evidencia.
- Políticas de duplicados: rechazar, omitir o actualizar.
- Separación entre cargas operativas y ejecuciones del piloto.
- Aplicación auditada de filas válidas.
- Descarga de plantilla XLSX y archivo CSV de errores.
- Restricciones por rol y organización.
- Protección de inventarios y periodos cerrados.

## 3. Pruebas automatizadas

- **158 pruebas recopiladas.**
- **158 nodos aprobados**, ejecutados por grupos aislados para evitar acumulación de recursos del cliente de pruebas.
- **10/10 pruebas específicas de V0.29 aprobadas** después del cierre final.
- Compilación de módulos Python aprobada.
- Sintaxis de scripts macOS aprobada.

## 4. Migración real desde V0.28

Se probó la migración sobre una copia de la base SQLite original V0.28.

Resultado:

- integridad SQLite de origen: correcta;
- línea base Alembic V0.28 reconocida;
- migración `0018 → 0019` aplicada;
- integridad SQLite de destino: correcta;
- revisión final: `20260802_0019`;
- 2 organizaciones conservadas;
- 3 inventarios conservados;
- 44 registros de actividad conservados;
- 2 documentos de evidencia conservados;
- nuevas tablas y columnas V0.29 creadas correctamente.

Los inventarios editables V0.28 se actualizan a V0.29; los inventarios cerrados o de otras líneas metodológicas conservan su trazabilidad.

## 5. Validación visual

Se revisó la nueva ventana en:

- escritorio: 1440 px;
- móvil: 390 px.

Resultado:

- sin desplazamiento horizontal global;
- tarjetas y formularios contenidos;
- selector de inventario adaptable;
- tablas con desplazamiento interno;
- menú lateral oculto correctamente al iniciar en móvil;
- corrección del parpadeo inicial del menú lateral.

## 6. Operación e instalador

Se reforzaron:

- copia consistente de SQLite mediante API de respaldo;
- reconocimiento de bases V0.28 sin tabla Alembic;
- migración automática y segura a V0.29;
- conservación de la base anterior antes de actualizar;
- selección y uso de la base V0.29 en macOS.

## 7. Resultado de alistamiento local

- base de datos disponible;
- almacenamiento local disponible;
- usuario administrador disponible;
- CSRF activo;
- cadena de auditoría íntegra;
- controles de seguridad operativos.

El modo local no se declara listo para exposición pública en Internet porque usa SQLite, HTTP y configuración de demostración. Para producción deben aplicarse las medidas descritas en `PRODUCCION.md` y `SECURITY.md`.

## 8. Pendientes controlados

No quedan desarrollos funcionales omitidos respecto de la V0.28. Para próximas iteraciones permanecen como líneas de mejora, no como pérdidas de alcance:

- conectores automáticos con sistemas externos;
- carga formal automática de archivos de evidencia desde la referencia textual de una fila;
- perfiles sectoriales adicionales;
- endurecimiento de despliegue productivo con PostgreSQL, HTTPS y secretos externos.
