# Calcula tu Huella — V1.4.0 Integración controlada

## Base

- Repositorio: `arendon7/CALCULAHUELLA`
- Rama fuente: `migration/canonical-v1.0.0`
- Commit fuente: `9a2c3a7cffb1adb403b5d99d9524b012dcca4433`
- Identificador canónico: `v1.0.0-canonica.20260805`
- Rama de integración: `integration/uiux-v1.4.0`

## Principio de no regresión

La integración no reemplaza motores, repositorios, migraciones, permisos, autenticación, modelos ni cálculos. La V1.4 modifica la presentación pública, la capa visual global y las pruebas/documentación asociadas.

## Etapa 1 — aplicación autenticada

La primera etapa conserva el CSS canónico como `app/static/css/app-canonical-v1.css` reutilizando exactamente su blob Git SHA `8534c3b398dab062b2fcc12a9115cc7383e99e27`.

El archivo `app/static/css/app.css` importa primero esa base y después `v1.4.css`. La reversión consiste en restaurar `app.css` al blob canónico y retirar las capas añadidas.

## Etapa 2 — experiencia pública

La segunda etapa incorpora:

- Landing pública servida por FastAPI mediante `public_base.html` y `public_home.html`.
- Hoja pública independiente, cargada después del CSS canónico, para aislar la nueva experiencia comercial.
- JavaScript público sin dependencias remotas y con navegación accesible.
- Sitio estático autocontenido para GitHub Pages dentro de `site/`.
- Pruebas de rutas reales, consistencia estática, reserva metodológica y reversibilidad del CSS.

## Separación de superficies

- `site/`: presentación pública estática para GitHub Pages. No simula persistencia empresarial ni reemplaza el backend.
- `app/templates/public_*`: presentación pública servida por FastAPI y conectada con rutas reales de diagnóstico, acceso y páginas legales.
- Aplicación autenticada: conserva la lógica y los datos canónicos; recibe únicamente la capa visual global.

## Validación

- Plantillas Jinja analizadas sin errores.
- JavaScript validado con `node --check`.
- Anclas y recursos estáticos consistentes.
- Sin referencias locales de desarrollo en las superficies públicas.
- 4 pruebas de integración pública aprobadas.
- Evidencia visual en escritorio, portátil y móvil: cero desbordamientos y cero errores de consola.

## Límites y lenguaje de confianza

La V1.4 no declara producción pública certificada, verificación automática ni cumplimiento garantizado. La plataforma organiza datos, evidencia, factores, cálculos, revisión y entregables; la verificación independiente corresponde a un tercero competente y a un alcance específico.

La publicación definitiva exige infraestructura, dominio, TLS, correo, almacenamiento, pruebas físicas y auditorías independientes conforme a la documentación canónica.
