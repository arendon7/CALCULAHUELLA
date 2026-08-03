# GitHub y despliegue

Este repositorio es la fuente canónica de **Calcula tu Huella** desde la migración de la versión 0.45.5.

## Migración inicial

1. Descarga `MIGRAR_CALCULAHUELLA_A_GITHUB.command`.
2. Conserva el ZIP `calcula_tu_huella_v0_45_5_completa_mac.zip` en Descargas.
3. Abre el archivo `.command`.
4. Autoriza GitHub cuando se solicite.
5. Revisa el pull request que se abrirá automáticamente.

El importador conserva código, migraciones, pruebas, recursos visuales, documentación, Docker, scripts y la aplicación fuente para macOS. Excluye `.env`, bases locales, cargas, evidencias, reportes, respaldos, logs, cachés, manifiestos y ZIP de distribución.

## Ramas

- `main`: versión estable y desplegable.
- `develop`: integración de iteraciones aprobadas.
- `feature/*`: cambios funcionales o visuales.
- `release/*`: estabilización previa a una versión.
- `migration/v0.45.5`: importación inicial controlada.

## Integración continua

GitHub Actions valida:

1. compilación de Python;
2. sintaxis de scripts macOS/Linux;
3. pruebas focalizadas de la línea v0.45.x;
4. construcción de la imagen Docker.

## Demostración pública

`render.yaml` define una demostración con aplicación Docker y PostgreSQL. La configuración mantiene usuarios demo y desactiva automatizaciones en segundo plano para simplificar el primer despliegue.

Antes de producción deben deshabilitarse usuarios demo, configurarse almacenamiento persistente de evidencias, dominio, correo, observabilidad y secretos reales.

## Releases

Los ZIP para macOS y sus archivos SHA-256 deben publicarse como activos de una GitHub Release. No se confirman dentro del árbol de código.
