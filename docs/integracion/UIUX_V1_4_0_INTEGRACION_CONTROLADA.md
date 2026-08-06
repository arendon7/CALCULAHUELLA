# Calcula tu Huella — V1.4.0 Integración controlada · Etapa 1

## Base inmutable

- Repositorio: `arendon7/CALCULAHUELLA`
- Rama fuente: `migration/canonical-v1.0.0`
- Commit fuente: `9a2c3a7cffb1adb403b5d99d9524b012dcca4433`
- Identificador canónico: `v1.0.0-canonica.20260805`
- Rama de integración: `integration/uiux-v1.4.0`

## Alcance de este commit

Esta primera etapa integra exclusivamente la capa visual global de la aplicación autenticada. No cambia rutas, modelos, migraciones, permisos, autenticación, repositorios, cálculos ni plantillas funcionales.

## Reversibilidad

El `app/static/css/app.css` canónico se conserva, sin alteraciones, como `app/static/css/app-canonical-v1.css` mediante el mismo blob Git SHA `8534c3b398dab062b2fcc12a9115cc7383e99e27`.

El nuevo archivo de entrada carga:

1. `app-canonical-v1.css` — base completa certificada.
2. `v1.4.css` — ajustes de identidad, jerarquía, espaciado y responsive.

La reversión consiste en devolver `app.css` al blob canónico y eliminar los dos archivos añadidos.

## Exclusiones expresas

La landing V1.4 completa, sus componentes públicos y el sitio estático se mantienen en el overlay local validado y se integrarán en un commit separado. Esta separación impide dejar la rama con referencias a recursos públicos incompletos.
