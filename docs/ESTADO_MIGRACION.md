# Estado de migración

Actualizado: 2026-08-03

## Completado

- Repositorio público definido como fuente canónica.
- v0.45.5 reconciliada contra v0.45.2–v0.45.4.
- Árbol canónico descomprimido y depurado preparado con 392 archivos.
- SHA-256 lógico del árbol: `407a3945b91ae0de96628373f7aeed41e7c979c98d0f12e8ab73266b7d6cdb09`.
- Cuatro PNG documentales optimizados sin pérdida y con píxeles idénticos.
- Exclusiones de secretos, bases, datos operativos, logs y cachés definidas.
- Instalación, arranque, pruebas, Makefile y Docker local preparados.
- CI configurado para Alembic, Jinja, regresión v0.45.x y Docker.
- Validación local: migraciones completas, 64 plantillas y pruebas críticas aprobadas por archivos.

## Estado de transferencia

El conector GitHub del chat administra archivos UTF-8 y objetos Git cuando el contenido ya está materializado, pero no puede leer un archivo binario local como entrada de `create_blob`. Por eso el árbol no se declara importado todavía.

Se generó un vehículo de transferencia único que contiene el repositorio descomprimido ya preparado. Al ejecutarlo, clona GitHub, crea `migration/v0.45.5-complete`, copia los 392 archivos, conserva permisos, realiza un commit y abre el Pull Request.

## Pendiente de cierre

- Confirmar la rama completa en GitHub.
- Ejecutar CI sobre el árbol importado.
- Revisión visual esencial.
- Fusionar a `main`.
- Crear etiqueta `v0.45.5-repository-baseline` y rama `develop`.
