# Frontend Kit v1 — integración progresiva

## Propósito

Integrar en Calcula tu Huella el sistema visual aprobado sin reescribir simultáneamente toda la interfaz ni alterar rutas, variables Jinja, formularios, permisos, modelos, migraciones, cálculos o datos.

## Fuente identificada

El Frontend Kit v1 define como componentes principales:

- `static/css/cth-ui.css`;
- `static/js/cth-ui.js`;
- `templates/app_shell.html`;
- `templates/components/ui_macros.html`;
- `templates/pages/`;
- `static/img/brand/`;
- `demo/index.html`.

La guía original exige un único logo oficial, navegación consistente, una acción primaria por pantalla, formularios con ayudas, estados visibles, tablas utilizables en móvil y ausencia de pérdida funcional.

## Tokens oficiales incorporados

Se versionaron en `app/static/design-tokens.json`:

| Token | Valor |
|---|---|
| Forest | `#0B3B2E` |
| Forest 2 | `#12533F` |
| Sage | `#A7C1A0` |
| Cream | `#F7F5EF` |
| Slate | `#1F2933` |
| Teal | `#2D6F73` |
| Earth | `#CA9A6C` |
| White | `#FFFFFF` |
| Line | `#DCE3DE` |
| Soft green | `#EDF4EE` |
| Danger | `#C94F4F` |

Tipografía: `Inter, Arial, sans-serif`.

Layout:

- ancho máximo: `1280px`;
- radio grande: `28px`;
- radio medio: `18px`;
- sombra: `0 18px 50px rgba(11,59,46,.10)`.

## Estrategia de compatibilidad

`app/static/css/cth-tokens.css` expone los tokens oficiales y asigna temporalmente las variables legacy a dichos valores. Esto permite:

1. corregir la paleta global sin modificar centenares de selectores en un solo cambio;
2. mantener estable la interfaz mientras se migran componentes;
3. identificar y retirar gradualmente las variables anteriores;
4. evitar que nuevas vistas introduzcan colores no gobernados.

## Superficies conectadas

- `base.html`;
- `public_base.html`;
- `login.html`;
- `supplier_portal.html`.

Todas utilizan:

```html
<link rel="stylesheet" href=".../css/app.css">
<link rel="stylesheet" href=".../css/cth-tokens.css">
```

La capa de tokens se carga después del CSS histórico para aplicar aliases sin alterar la estructura existente.

## Estado de los activos gráficos

El Frontend Kit v1 referencia:

```text
static/img/brand/
  logo-oficial.png
  logo-oficial-blanco.png
  favicon-64.png
  favicon-256.png
```

También existen demostraciones autocontenidas con el PNG oficial embebido en base64. Estos archivos prueban la existencia y uso del activo, pero no autorizan redibujarlo ni sustituirlo por una aproximación.

Hasta materializar los binarios exactos en el repositorio:

- los SVG actuales permanecen únicamente por compatibilidad;
- no se eleva la versión a 0.45.6;
- no se retiran las referencias legacy;
- el PR continúa como borrador.

## Orden de migración de componentes

1. Tokens y paleta.
2. Activos maestros exactos.
3. Botones, campos, estados y tarjetas.
4. Shell interno.
5. Login.
6. Onboarding.
7. Dashboard.
8. Fuentes y captura.
9. Calidad, revisión y cierre.
10. Informes y reducción.
11. Retiro del CSS legacy.

## Controles automáticos

Las pruebas verifican:

- valores exactos de los tokens;
- carga de `cth-tokens.css` en superficies base;
- tema de navegador `#0B3B2E`;
- descriptor y claim oficiales;
- prohibición de redibujos y placeholders;
- permanencia de la versión 0.45.5 mientras no exista el maestro exacto.

El verificador `scripts/brand/verify_master_assets.py` controla la futura instalación de hashes, dimensiones y referencias activas.

## Criterio de cierre

La integración inicial del Frontend Kit v1 queda cerrada cuando:

- los cuatro activos exactos están en Git;
- el manifiesto contiene SHA-256, dimensiones y peso;
- todas las superficies base usan los nuevos activos;
- los SVG legacy dejan de estar referenciados;
- CI y revisión visual responsive pasan;
- la versión se eleva de forma consistente a 0.45.6.
