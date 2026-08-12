# Landing craft pass · V2.1

## Routing aplicado

La iteración pública usa el routing vigente de `cth-web-design`:

- **Taste**: dirección primaria de marketing público y composición;
- **Impeccable**: crítica, jerarquía, craft floor y pulido;
- **Emil Design Engineering**: motion e interacción intencional;
- **Vercel Web/Writing Guidelines**: accesibilidad, semántica, metadata y claridad;
- **Binario Content/Asset Factory**: estructura narrativa y verdad de contenido.

Los snapshots y commits usados son los fijados en `docs/design/WEB_DESIGN_SKILL_REGISTRY.json`.

## Cambios de dirección

- Hero centrado en el producto y su cadena dato → evidencia → cálculo → revisión → decisión.
- Eliminación de eyebrows repetidos, numeración decorativa y varias filas de cards equivalentes.
- Narrativa editorial-operativa asimétrica para valor, roles, casos de uso y entregables.
- Pricing anual visible con referencias COP $1.300.000 / $3.300.000 / $8.300.000 y factores que pueden modificar alcance/precio.
- FAQ abierta, no accordion genérico.
- Motion limitado a un momento de hero y feedback de interacción, con `prefers-reduced-motion`.
- Metadatos SEO/Open Graph y navegación con Precios explícito.
- Preview de plataforma sin glifos Unicode como sistema de iconos.
- CTA final reubicado después del diagnóstico.

## QA de navegador

Workflow: `.github/workflows/site-preview-qa.yml`

Gate: `scripts/site_preview_gate.py`

Valida Chromium real en desktop 1440 px y móvil 390 px:

- overflow horizontal;
- H1 único;
- ausencia de eyebrows visibles;
- enlaces muertos;
- descubribilidad de precios y demo;
- precios canónicos de la landing;
- diagnóstico y precio de ruta;
- navegación de la app preview y selector de rol;
- menú móvil;
- `prefers-reduced-motion`;
- contención del bloque de experiencia;
- orden final diagnóstico → CTA → nota de preview.

La evidencia incluye screenshots y JSON de resultados como artifact `site-preview-qa`.