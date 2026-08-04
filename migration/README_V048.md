# Migración canónica V0.48.0

## Decisión

La línea canónica del producto deja de ser V0.45.5. La fuente más reciente validada es:

```text
calcula_tu_huella_v0_48_0_portafolio_reduccion_mac.zip
```

V0.48.0 se construyó sobre V0.47.0 y V0.46.1 autocontenidas. Mantiene compatibilidad con factores, conversiones, GWP, fórmulas, modelos, migraciones y datos históricos.

## Evidencia publicada

- SHA-256 del ZIP: `921a97f8cf6a74c60161c9e96afcaed13c713afebdf09dedc8309c77a961b5d3`.
- SHA-256 lógico del árbol: `91410e981bf93e2c036cf544cc190dc57c39f5c464e1793cea314b4b7d210eef`.
- 406 archivos funcionales.
- 284 rutas.
- 109 modelos ORM y tablas.
- 65 plantillas Jinja.
- 31 archivos de pruebas.
- 103 pruebas funcionales focalizadas y 7 controles de seguridad aprobados.
- Alembic `20260803_0029`.

## Capacidades que deben conservarse

- dirección ejecutiva del inventario;
- recorrido de seis etapas;
- ocho puertas ponderadas de entrega;
- control de publicación;
- ficha ejecutiva, informe ejecutivo, informe técnico y memoria Excel;
- portafolio de reducción dirigido;
- brecha y cobertura frente a meta;
- preparación y clasificación por medida;
- vencimientos, responsables y embudo de ejecución;
- trayectoria anual;
- API `/api/reduccion/resumen`;
- exportación `/reduccion/exportar.xlsx`.

## Identidad visual obligatoria

La fuente debe contener los activos exactos:

```text
logo-oficial.png
logo-oficial-blanco.png
favicon-64.png
favicon-256.png
```

La landing autocontenida y el Frontend Kit también documentan al menos ocho imágenes de módulos. Entre ellas:

```text
01_dashboard_climatico.png
02_calidad_de_datos.png
08_metodologia_y_alcances.png
```

No se aceptan los SVG anteriores `brand-primary.svg`, `brand-reversed.svg`, `brand-symbol.svg`, `logo.svg`, `logo-white.svg` o `favicon.svg` como sustitutos de la Marca Maestra.

## Separación del PR anterior

El PR visual V0.45.6 contiene trabajo valioso de UX, pero fue construido sobre una fuente anterior. No debe fusionarse sobre `develop` antes de reconciliarlo con V0.48.0. La nueva secuencia es:

1. importar y validar V0.48.0 exacta;
2. ejecutar la vista previa en Codespaces;
3. comparar los componentes UX del PR anterior contra la nueva fuente;
4. portar únicamente mejoras no presentes en V0.48.0;
5. cerrar o reemplazar el PR anterior;
6. fusionar una línea única y coherente.

## Criterio para declarar completada la migración

- ZIP exacto importado por Actions;
- cuatro activos oficiales presentes y referenciados;
- imágenes modulares presentes;
- versión runtime `0.48.0`;
- 284 rutas, 109 modelos y 65 plantillas comprobados;
- Alembic desde base vacía;
- pruebas focalizadas y seguridad aprobadas;
- Docker construido;
- Codespaces abierto y verificado visualmente;
- PR nuevo revisado contra `develop`.
