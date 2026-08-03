# V0.43 · Certificación operativa de versión

## Propósito

Convertir la preparación productiva en una evidencia reproducible y auditable. La certificación enlaza la versión de la aplicación, el respaldo, la restauración, la puerta de despliegue, los servicios externos y los hashes de integridad.

## Flujo

1. Crear respaldo consistente de base, evidencias e informes.
2. Verificar ZIP, rutas seguras, manifiesto y SHA-256.
3. Restaurar la base en un entorno temporal aislado.
4. Ejecutar la puerta local o estricta.
5. Replicar el respaldo cuando exista almacenamiento externo.
6. Generar el paquete ZIP de evidencia.
7. Replicar y verificar el certificado en almacenamiento externo.
8. Persistir estado, alcance, hashes, bloqueos y responsable.

## Estados

- `Validación local`: controles internos aprobados; no autoriza publicación.
- `Bloqueada`: existe al menos un control crítico pendiente.
- `Certificada`: modo estricto aprobado, servicios reales disponibles y evidencia replicada.

## Evidencia

El paquete incluye:

- `certificacion.json`;
- `respaldo_manifest.json`;
- `restauracion.json`;
- `despliegue.json`;
- `LEEME.txt`.

Se registran tres hashes independientes: respaldo, certificado lógico y archivo ZIP de evidencia.

## Stack de ensayo

`13_INICIAR_STACK_ENSAYO.command` levanta PostgreSQL, MinIO, Caddy, Prometheus, Alertmanager y Grafana. Después espera sus endpoints de salud y ejecuta la certificación estricta. Si un servicio no responde, la publicación queda bloqueada.
