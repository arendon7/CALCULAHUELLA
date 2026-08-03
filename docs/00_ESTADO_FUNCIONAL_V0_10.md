# Estado funcional V0.10

## Aprobado

- Configuración por ambientes.
- SQLite local y PostgreSQL productivo.
- Seguridad de sesiones y contraseñas.
- Limitación de intentos de login.
- Cabeceras de seguridad.
- Diagnóstico de salud y preparación.
- Panel administrativo de operación.
- Respaldos consistentes y descargables.
- Restauración SQLite mediante script.
- Docker Compose con PostgreSQL y Caddy HTTPS.
- Inicialización productiva sin datos demo.
- Migración básica desde V0.9.

## Deuda controlada

- Incorporar Alembic antes de migraciones de esquema complejas.
- Centralizar rate limiting para despliegues con varias réplicas.
- Añadir almacenamiento de objetos externo para alta disponibilidad.
- Ejecutar una auditoría de seguridad independiente antes de comercialización masiva.

## Pruebas

32 pruebas automáticas aprobadas.
