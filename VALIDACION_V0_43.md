# Validación técnica · Calcula tu Huella V0.43

## Línea base

V0.43 fue construida sobre el paquete completo V0.42 reconciliado. Conserva todos sus módulos, cálculos, metodología, piloto Greenatics, instalación Mac y operación controlada.

## Resultado funcional

- 218 pruebas recopiladas y aprobadas en procesos aislados.
- 87 recorridos históricos del núcleo aprobados.
- 131 pruebas especializadas V0.21–V0.43 aprobadas.
- 261 rutas registradas.
- 57 rutas con propiedad explícita de dominio.
- Cero duplicados de método y ruta.
- 104 modelos ORM y 104 tablas de aplicación.
- 4 repositorios y 4 servicios explícitos.

## Migración real V0.42 → V0.43

Antes y después:

- 2 organizaciones;
- 3 inventarios;
- 44 registros de actividad;
- 68 cálculos.

Resultado:

- revisión Alembic `20260803_0027`;
- nueva tabla `release_certifications`;
- inventarios activos actualizados a `0.43`;
- `PRAGMA integrity_check = ok`;
- sin recálculo de emisiones históricas.

También se validó una instalación desde base vacía: 104 tablas de aplicación, organización demostrativa creada correctamente y cadena Alembic completa.

## Validaciones nuevas

- validación local con respaldo, restauración, despliegue y paquete ZIP firmado;
- la validación local conserva `production_approved = false`;
- certificación estricta bloqueada cuando faltan servicios externos reales;
- hash SHA-256 del respaldo, certificado lógico y paquete de evidencia;
- paquete con `certificacion.json`, manifiesto del respaldo, restauración y despliegue;
- réplica externa exigida únicamente para certificación productiva;
- comprobaciones vivas de almacenamiento, Prometheus, Alertmanager y Grafana;
- incidentes de despliegue resueltos automáticamente al recuperarse el control;
- alertas `resolved` de Alertmanager cierran el incidente;
- scripts macOS validados con `bash -n`;
- instalador conserva certificados, respaldos, importaciones, informes y evidencias entre actualizaciones;
- comandos administrativos ejecutables directamente sin depender de un `PYTHONPATH` externo;
- Docker Compose parseado correctamente.

## Limitación verificable

No se ejecutó una certificación productiva viva porque este entorno no dispone de Docker ni PostgreSQL. `13_INICIAR_STACK_ENSAYO.command` levanta el stack y ejecuta `scripts/certify_release.py --strict` en un Mac con Docker Desktop. Hasta entonces, la plataforma mantiene la certificación productiva como bloqueada.
