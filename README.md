# Calcula tu Huella

**Plataforma digital de gestión de huella de carbono**  
Convierte tus datos en decisiones climáticas.

Repositorio canónico del producto. La migración parte de la **v0.45.5** y continuará mediante ramas, pruebas automáticas, pull requests y despliegues reproducibles.

## Estado de migración

- Rama de trabajo: `migration/v0.45.5`
- Base funcional: v0.45.5
- Fuente anterior: paquete completo para macOS
- Objetivo: código navegable, CI, despliegue y Releases desde GitHub

## Flujo de ramas

- `main`: versión estable y desplegable.
- `develop`: integración de iteraciones aprobadas.
- `feature/*`: mejoras funcionales o visuales.
- `release/*`: estabilización previa a una versión.

## Importación inicial

La importación masiva conserva código, migraciones, pruebas, plantillas, recursos visuales, documentación y scripts. Excluye datos locales, secretos, bases, respaldos, reportes generados, cachés y ZIP de distribución.

Consulta el [Issue #1](https://github.com/arendon7/CALCULAHUELLA/issues/1) para el control de la migración.