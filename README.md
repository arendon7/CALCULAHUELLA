# Calcula tu Huella

**Plataforma digital de gestión de huella de carbono**  
Convierte tus datos en decisiones climáticas.

Repositorio canónico del producto. La migración parte de la **v0.45.5** y continuará mediante ramas, pruebas automáticas, pull requests y despliegues reproducibles.

## Ejecución local

```bash
git clone https://github.com/arendon7/CALCULAHUELLA.git
cd CALCULAHUELLA
./scripts/dev/setup.sh
./scripts/dev/run.sh
```

La aplicación estará disponible en `http://127.0.0.1:8765`.

Con Docker y PostgreSQL:

```bash
docker compose -f docker-compose.local.yml up --build
```

Consulta `docs/DESARROLLO_LOCAL.md` para configuración, pruebas y persistencia.

## Estado de migración

- Rama de trabajo: `migration/v0.45.5`.
- Base funcional: v0.45.5.
- Código fuente objetivo: contenido descomprimido y depurado del paquete validado para macOS.
- Objetivo: código navegable, CI, despliegue y Releases desde GitHub.
- Validación local aprobada: Alembic, 64 plantillas, 18 pruebas críticas y rutas HTTP principales.

## Flujo de ramas

- `main`: versión estable y desplegable.
- `develop`: integración de iteraciones aprobadas.
- `feature/*`: mejoras funcionales o visuales.
- `release/*`: estabilización previa a una versión.

## Importación inicial

La importación conserva código, migraciones, pruebas, recursos visuales, documentación y scripts. Excluye datos locales, secretos, bases, respaldos, reportes generados, cachés y ZIP de distribución.

Consulta el [Issue #1](https://github.com/arendon7/CALCULAHUELLA/issues/1) y el [PR #2](https://github.com/arendon7/CALCULAHUELLA/pull/2) para seguir la migración.
