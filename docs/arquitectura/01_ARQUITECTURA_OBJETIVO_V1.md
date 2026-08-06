# Arquitectura objetivo para V1.0

## Problema actual

El sistema conserva una aplicación funcional, pero `app/main.py` y `app/database.py` concentran demasiadas responsabilidades. La refactorización debe ser incremental para no romper los flujos ya validados.

## Estructura objetivo

```text
app/
  core/                 configuración, sesión, auditoría, errores
  auth/                 usuarios, membresías, permisos
  organizations/        empresas y sedes
  inventories/          inventarios, límites y versiones
  activity_data/        solicitudes, datos y evidencias
  factors/              biblioteca, GWP y conversiones
  calculations/         motor y casos patrón
  review/               observaciones, aprobación y cierre
  reporting/            PDF, Excel y paquetes
  reductions/           metas, acciones y escenarios
  suppliers/            alcance 3 y portal de proveedor
  verification/         acceso y hallazgos externos
  climate/              riesgo, impacto y divulgación avanzada
  platform/             operación, SaaS, soporte y comercial
```

Cada dominio debe separar:

- `router.py`: interfaz HTTP;
- `schemas.py`: validación de entradas y salidas;
- `service.py`: reglas de negocio;
- `repository.py`: acceso a datos;
- `models.py`: entidades persistentes;
- `permissions.py`: autorización del dominio;
- `tests/`: pruebas unitarias e integrales.

## Secuencia segura

1. Extraer política de acceso y registro de producto —iniciado en V0.21—.
2. Extraer rutas de consolidación, autenticación e inventarios.
3. Extraer cálculo y metodología con pruebas patrón.
4. Dividir modelos sin cambiar nombres de tablas.
5. Introducir repositorios y transacciones explícitas.
6. Mantener migraciones compatibles durante toda la refactorización.
