# Acta de certificación de la versión canónica

- Producto: Calcula tu Huella
- Versión: `1.0.0`
- Identificador: `v1.0.0-canonica.20260805`
- Fecha de validación: `2026-08-05T23:42:01-05:00`
- Repositorio objetivo: `arendon7/CALCULAHUELLA`

## Resultado

La estructura canónica única fue validada correctamente. No contiene bases de datos de ejecución, secretos ni árboles duplicados de la aplicación para Mac y Windows.

## Evidencia ejecutada

- Verificación del manifiesto SHA-256: aprobada.
- Compilación Python: aprobada.
- Sintaxis JavaScript: aprobada.
- JSON: 11 archivos válidos.
- YAML: 15 archivos válidos.
- Migración desde base vacía: aprobada hasta `20260805_0036`, con 121 tablas.
- Pruebas smoke: 9 aprobadas; 405 no seleccionadas.
- Vista previa estática: seis recursos críticos respondieron HTTP 200.
- Certificación funcional heredada de Iteración 14: 414 pruebas Mac; 411 Windows y 3 omisiones exclusivas de macOS.

## Alcance de publicación

La carpeta `site/` está preparada para GitHub Pages. La aplicación completa conserva backend FastAPI y requiere un servicio de ejecución y base de datos; no se presenta la vista estática como sustituto del sistema transaccional.

## Estado del repositorio

El repositorio remoto no fue modificado durante esta preparación. El reemplazo se realizará posteriormente mediante respaldo del `main`, rama de migración, validación CI y cambio controlado.
