# Estado funcional V0.12

## Aprobado y funcional

- Operación multiempresa por membresías.
- Cambio de organización con aislamiento de consultas.
- Roles distintos por organización.
- Creación de nuevas organizaciones desde el portafolio.
- Automatizaciones configurables y ejecutables.
- Cálculo de próxima ejecución por zona horaria.
- Historial de ejecuciones, procesados y errores.
- Recordatorios de datos, observaciones y proveedores.
- Resumen ejecutivo y recálculo programado.
- API de entrada para datos de actividad.
- Autenticación por clave almacenada como hash.
- Rotación y desactivación de claves.
- Registro de eventos de integración.
- Migración desde V0.11.

## Alcance deliberadamente limitado

- Microsoft 365, Google Drive y ERP pueden registrarse, pero requieren credenciales y adaptadores específicos para conectarse realmente.
- El programador local se ejecuta en el proceso de `run.py`; producción debe utilizar un trabajador único.
- No se implementan webhooks entrantes arbitrarios ni ejecución de código externo.

## Pruebas

41 pruebas automáticas aprobadas, incluyendo aislamiento multiempresa, creación de membresías, ejecución de automatizaciones, carga mediante API y rechazo de claves inválidas.
