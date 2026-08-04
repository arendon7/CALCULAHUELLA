# Migración canónica V0.49.0

## Decisión

La fuente más reciente validada del proyecto es:

```text
calcula_tu_huella_v0_49_0_dual_mac_windows.zip
```

V0.49.0 se construyó sobre V0.48.0 y añade:

1. landing pública comercial y metodológicamente prudente;
2. distribución autónoma para macOS y Windows;
3. selección específica de uno o varios factores de emisión por dato.

## Evidencia publicada

- SHA-256 del ZIP: `b83066b35490bfed325ee2d74cf38cfeb14c216c0a63632c19140a777f763c06`.
- MAC: 424 archivos físicos y 413 funcionales declarados.
- WINDOWS: 401 archivos físicos y 390 funcionales declarados.
- 287 rutas.
- 110 modelos ORM.
- 65 plantillas Jinja.
- 10 dominios y 75 rutas administradas por dominio.
- 108 pruebas funcionales y 7 controles de seguridad aprobados.
- Alembic `20260804_0030`.

## Estado del binario

La Biblioteca del proyecto conserva el manifiesto, la validación y el checksum, pero el ZIP no está montado como archivo binario en el entorno activo. La importación no se declara ejecutada hasta que el archivo exacto sea cargado en `migration/inbox/` y GitHub Actions verifique su hash.

## Runtime canónico y distribución Windows

La distribución `MAC/` fue ejecutada durante la validación original y se importa como runtime canónico del repositorio.

El verificador exige que `app/`, `migrations/`, `tests/`, `scripts/` y los archivos centrales sean idénticos en `MAC/` y `WINDOWS/`.

Las diferencias específicas de Windows se guardan en:

```text
platform/windows/overlay/
platform/windows/OVERLAY_MANIFEST.json
```

Esto permite reconstruir la distribución Windows sin mantener dos copias completas del backend dentro de GitHub.

## Capacidades que deben conservarse

- landing con propuesta de valor, proceso, planes, equipo, Greenatics y contacto;
- solicitud comercial trazable;
- diagnóstico sectorial;
- selección heredada o específica de factores por dato;
- candidatos explicados por compatibilidad;
- bloqueo cuando no existe conversión de unidades;
- justificación obligatoria;
- selecciones múltiples activas;
- retorno automático al factor heredado;
- congelación del factor utilizado en el cálculo;
- dirección ejecutiva y control de entrega;
- informes y memoria de cálculo;
- portafolio de reducción dirigido.

## Identidad visual obligatoria

Cada distribución debe contener:

```text
logo-oficial.png
logo-oficial-blanco.png
favicon-64.png
favicon-256.png
```

También se exigen al menos ocho imágenes modulares, incluidas:

```text
01_dashboard_climatico.png
02_calidad_de_datos.png
08_metodologia_y_alcANCES.png
```

Los SVG históricos no son sustitutos válidos de la Marca Maestra.

## Secuencia de migración

1. cargar el ZIP exacto en `migration/inbox/`;
2. verificar hash, estructura dual, paridad del núcleo y activos;
3. importar `MAC/` al árbol raíz;
4. generar el overlay Windows;
5. aplicar Alembic hasta `20260804_0030`;
6. validar 287 rutas, 110 modelos y 65 plantillas;
7. ejecutar pruebas V0.46–V0.49 y seguridad;
8. construir Docker;
9. abrir Codespaces y revisar la aplicación;
10. reconciliar las mejoras UX del PR #4;
11. fusionar una única línea coherente a `develop`.

## Criterio de cierre

- ZIP exacto importado por Actions;
- runtime `0.49.0`;
- cuatro activos oficiales presentes y referenciados;
- landing y formulario público operativos;
- tabla `activity_factor_selections` presente;
- migración `20260804_0030` aplicada;
- overlay Windows generado;
- CI y Docker aprobados;
- Codespaces revisado en escritorio y móvil;
- PR canónico revisado contra `develop`.
