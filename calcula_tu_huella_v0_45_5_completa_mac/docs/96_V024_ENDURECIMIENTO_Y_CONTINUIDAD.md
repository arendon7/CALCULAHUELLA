# V0.24 · Endurecimiento y continuidad operativa

## Objetivo

Reducir riesgos técnicos antes de la beta cerrada sin ampliar el alcance funcional del producto.

## Controles incorporados

1. Protección CSRF para formularios del navegador.
2. Bloqueo persistente de intentos de acceso.
3. Cadena SHA-256 de eventos de auditoría por organización.
4. Identificador de correlación por solicitud.
5. Registro estructurado JSONL sin parámetros de consulta.
6. Validación de firma, tipo y estructura de archivos.
7. Verificación de integridad de respaldos.
8. Diagnóstico operativo ampliado.
9. Migración directa desde V0.23.
10. Conservación del instalador de doble clic para macOS.

## Decisiones de diseño

- Las rutas API quedan fuera del CSRF porque usan claves o firmas específicas.
- El token CSRF se transporta mediante cookie `SameSite=Lax` y campo oculto.
- Los correos e IP usados en limitación de acceso no se almacenan en claro.
- La inicialización solo completa hashes ausentes de eventos heredados; nunca recalcula hashes existentes para no ocultar manipulaciones.
- La validación de archivos es defensiva y no reemplaza un antivirus empresarial.

## Pendientes para producción

- Redis o servicio distribuido de rate limiting para múltiples réplicas.
- Centralización de logs y alertas.
- Escaneo antimalware de adjuntos.
- Gestión externa de secretos.
- SAST, DAST, análisis de dependencias y prueba de penetración.
- Ensayo formal de recuperación y continuidad.
