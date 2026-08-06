# Reemplazo controlado del repositorio GitHub

## Destino

- Repositorio: `arendon7/CALCULAHUELLA`
- Rama principal: `main`
- Permisos confirmados: administración y escritura

## Principio

La versión canónica está preparada para reemplazar el árbol actual, que conserva archivos históricos, duplicados y una versión anterior. El reemplazo no debe destruir la trazabilidad Git.

## Procedimiento previsto

1. Registrar el SHA vigente de `main`.
2. Crear una rama o etiqueta de respaldo: `archive/pre-canonical-20260805`.
3. Crear una rama de migración: `release/v1.0.0-canonical`.
4. Construir un árbol Git nuevo desde esta carpeta canónica, sin heredar archivos obsoletos.
5. Crear un commit único de sustitución sobre la rama de migración.
6. Ejecutar CI, pruebas, escaneo de secretos y despliegue de la vista Pages.
7. Revisar el diff como reemplazo integral.
8. Integrar a `main` solo después de comprobar Pages y el despliegue backend.

## GitHub Pages

El workflow `.github/workflows/pages.yml` publica exclusivamente `site/`. Esa vista permite presentar y navegar una demostración estática. La aplicación FastAPI completa debe desplegarse en un servicio que ejecute contenedores o Python y suministre PostgreSQL/almacenamiento.

## Elementos que se eliminarán del repositorio anterior

- Duplicados y manifiestos de versiones históricas.
- Paquetes locales generados y bases de datos.
- Estructuras antiguas sustituidas por esta fuente canónica.
- Documentos de validación obsoletos que no formen parte de `docs/`.

## Salvaguardas

- No forzar `main` sin rama de respaldo.
- No cargar `.env`, bases SQLite, secretos, respaldos ni uploads.
- No presentar GitHub Pages como la aplicación completa.
