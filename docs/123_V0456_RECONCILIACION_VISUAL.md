# V0.45.6 — Reconciliación visual y contrato de marca

## Objetivo

Cerrar la coexistencia de identidades, descriptores y claims dentro de Calcula tu Huella antes de continuar la expansión visual y funcional.

Esta etapa no modifica rutas, modelos, migraciones, fórmulas, datos ni permisos.

## Contrato aprobado

- **Marca:** Calcula tu Huella
- **Descriptor:** Plataforma digital de gestión de huella de carbono
- **Claim:** Convierte tus datos en decisiones climáticas
- **Marca gráfica aprobada:** composición circular en forma de C que envuelve barras ascendentes e integra una hoja.
- **Regla:** el logo debe instalarse desde el archivo maestro exacto. No se permite redibujarlo, reinterpretarlo, deformarlo ni sustituirlo por un placeholder.

## Fuentes visuales reconciliadas

La auditoría recuperó como referencias aprobadas:

- `00_GUIA_INTEGRACION.md` — Frontend Kit v1;
- `00_LEEME_PRIMERO.md` — Integración visual V0.42 → V0.43;
- `static/img/brand/` — activos oficiales exactos del kit;
- sitio público autocontenido con `logo-oficial.png` embebido;
- experiencia interna autocontenida con el mismo activo.

## Hallazgos en v0.45.5

1. `brand-primary.svg`, `brand-reversed.svg` y `brand-symbol.svg` corresponden al sistema anterior de huella/gráfico.
2. El manifiesto los declaraba erróneamente como activos canónicos.
3. La landing, el login, el shell interno y el footer utilizaban:
   - “Plataforma profesional de huella de carbono”;
   - “Mide. Comprende. Reduce.”
4. El repositorio carece todavía de los binarios oficiales exactos del Frontend Kit v1.
5. La biblioteca visual existente no constituye aún un paquete de producción completo.

## Cambios aplicados en esta rama

- Descriptor oficial aplicado a landing, metadatos, login y footer.
- Claim oficial aplicado a landing, login y shell interno.
- Mensajes heredados retirados de las superficies principales.
- `brand-manifest.json` convertido en contrato verificable.
- SVG actuales reclasificados como activos de compatibilidad, no como logo oficial.
- Redibujo y placeholders bloqueados explícitamente.
- Pruebas automáticas actualizadas para impedir regresiones de copy y falsas declaraciones de activos canónicos.

## Estado del logo

La sustitución binaria no se ejecuta en esta rama hasta recuperar los archivos maestros exactos. Mientras tanto:

- los SVG heredados continúan sirviendo para no romper la interfaz;
- no se declara cerrada la v0.45.6;
- la versión de aplicación permanece en `0.45.5`;
- no se generará una Release visual definitiva.

## Activos requeridos para cerrar

Como mínimo:

- `logo-oficial.png` o equivalente maestro transparente;
- `logo-oficial-blanco.png`;
- favicon oficial en 64 px;
- favicon o icono oficial en 256 px;
- evidencia de dimensiones y SHA-256.

Se recomienda conservar los nombres bajo:

```text
app/static/img/brand/
  logo-oficial.png
  logo-oficial-blanco.png
  favicon-64.png
  favicon-256.png
  manifest.json
```

## Criterios de aceptación

1. Un único logo oficial en sitio público, login, aplicación interna y favicons.
2. Ninguna referencia activa a los SVG heredados.
3. Descriptor y claim consistentes.
4. Sin redibujos o sustitutos.
5. Pruebas de marca en verde.
6. Revisión visual a 1440 px, 1024 px, 768 px y 390 px.
7. Contraste, foco y navegación móvil validados.
8. CI completa en verde.
9. Versión elevada a `0.45.6` solo después del cierre binario.

## Siguiente bloque después del cierre

1. Biblioteca visual de producción por módulo.
2. Landing pública ampliada con imágenes propias.
3. Evidencias y expediente documental.
4. Calidad, revisión y aprobación.
5. Informes y planes de reducción.
