# Revisión interna de seguridad · Calcula tu Huella V1.0.0

## Alcance

Revisión interna basada en controles aplicables de OWASP ASVS 5.0.0 para una aplicación web empresarial. No es un pentest independiente ni una certificación OWASP.

## Controles verificados

- autenticación y endurecimiento de contraseñas;
- limitación persistente de intentos;
- sesiones con SameSite y opción Secure;
- CSRF activo;
- encabezados de seguridad;
- separación por organización y roles;
- validación de archivos, extensiones, tamaño y contenido;
- protección de rutas administrativas;
- trazabilidad y cadena de auditoría;
- copia, firma, verificación y restauración de respaldos;
- secretos fuera del código en producción;
- trusted hosts y HTTPS exigidos en producción;
- validación de webhooks mediante secreto;
- bloqueo de producción cuando faltan controles obligatorios.

## Resultado

**Aprobada como revisión de seguridad interna para despliegue controlado.**

## Riesgo residual

Antes de exposición pública con datos reales se mantiene como requisito:

1. prueba de penetración independiente;
2. revisión de dependencias contra vulnerabilidades vigentes;
3. configuración real de TLS, PostgreSQL, almacenamiento, SMTP y respaldos;
4. prueba de recuperación y monitoreo en la infraestructura definitiva;
5. prueba física de instaladores Windows.

Esta revisión no debe describirse como auditoría independiente.
