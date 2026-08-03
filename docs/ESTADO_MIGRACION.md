# Estado de migración

Actualizado: 2026-08-03

## Completado

- Repositorio público definido como fuente canónica.
- Rama `migration/v0.45.5` y PR #2 activos.
- v0.45.5 seleccionada como base tras reconciliar v0.45.2–v0.45.4.
- Inventario y clasificación reproducibles definidos.
- Exclusiones de secretos, datos locales y artefactos generados configuradas.
- Scripts de instalación, arranque y pruebas locales creados.
- Docker Compose local con PostgreSQL definido.
- Comandos Make normalizados.
- GitHub Actions configurado para Alembic, Jinja, pruebas y Docker.
- Validación local aprobada:
  - migraciones hasta v0.45;
  - 64 plantillas;
  - 18 pruebas críticas;
  - portada, acceso y diagnóstico HTTP 200.

## En curso

- Transferencia del árbol fuente completo descomprimido a la rama.
- Verificación SHA-256 después de la transferencia.

## Pendiente

- Confirmar los recursos PNG documentales de `docs/visual`.
- Ejecutar GitHub Actions sobre el árbol completo.
- Probar Docker/PostgreSQL dentro de CI.
- Revisar visualmente las pantallas esenciales.
- Fusionar a `main`.
- Crear etiqueta `v0.45.5-repository-baseline` y rama `develop`.
- Generar la primera Release desde GitHub.
