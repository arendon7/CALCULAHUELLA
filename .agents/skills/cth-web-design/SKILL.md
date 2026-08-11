---
name: cth-web-design
description: Orquesta diseño web, UX, contenido, assets, motion y QA visual de Calcula tu Huella sin alterar metodología, marca canónica ni contratos funcionales.
---

# Calcula tu Huella · Web Design Orchestrator

Usa este skill para cualquier cambio visible en landing, aplicación, formularios, dashboards, tablas, onboarding, informes web, estados, responsive o motion.

## 1. Carga primero las verdades del proyecto

Antes de proponer UI:

1. Lee `docs/design/WEB_DESIGN_SKILL_REGISTRY.json`.
2. Conserva el `domain_truth_lock`, `brand_truth_lock` y `functional_truth_lock`.
3. Identifica la superficie: `public_marketing`, `product_ui`, `motion`, `content` o `final_qa`.
4. Revisa la pantalla existente y su flujo real; no diseñes desde una descripción aislada si existe implementación.
5. Recupera decisiones previas relevantes antes de introducir un patrón nuevo.

Si dos fuentes discrepan, la decisión canónica más reciente del proyecto prevalece sobre un skill externo.

## 2. Clasifica y enruta

### Public marketing
Dirección visual: Taste + Binario IA Content/Asset Factory.  
Crítica/pulido: Impeccable.  
Art direction adicional: OpenAI frontend-skill.  
Motion: Emil solo después de fijar jerarquía, contenido y layout.

### Product UI
Primarios: Impeccable + Vercel Web Design Guidelines + Binario UX System/Component Intelligence.  
Taste es solo referencia anti-genérica y **no** dirige dashboards, tablas ni workflows multietapa.  
Prioriza legibilidad, jerarquía operacional, densidad apropiada, estados, errores y velocidad de tarea.

### Motion
Emil Design Engineering dirige microinteracciones y motion.  
Debe existir fallback `prefers-reduced-motion`; la animación nunca bloquea tareas ni oculta estados.

### Content
Binario Content Factory dirige la narrativa por pantalla.  
Usa Writing Guidelines e Impeccable para claridad, microcopy, errores, ayudas, estados vacíos y CTA.

## 3. Flujo obligatorio

`contexto → verdad → arquitectura de información → contenido → dirección visual → prototipo/cambio → crítica → accesibilidad → responsive → navegador real → evidencia → revisión humana`

No empieces por decoración.

Para cambios sustanciales, compara al menos dos alternativas antes de consolidar una dirección, excepto cuando la solución ya esté fijada por el design system o por una decisión canónica.

## 4. Evidencia mínima

Toda superficie modificada debe demostrar según aplique:

- escritorio y móvil;
- navegación por teclado y foco visible;
- estado vacío;
- estado de error;
- estado de alta densidad/carga;
- texto real o demo coherente, no lorem ipsum;
- motion reducido;
- navegador real mediante los journeys existentes;
- ausencia de desbordamiento horizontal;
- una acción primaria claramente reconocible;
- consistencia con componentes existentes;
- logo clásico exacto, nunca redibujado.

No declares mejora visual solo por inspección de código.

## 5. Criterio de adopción

Un patrón nuevo entra al producto solo si:

1. resuelve una necesidad de usuario o comunicación identificada;
2. no duplica un componente existente sin razón;
3. pasa los gates pertinentes;
4. tiene evidencia visual/funcional;
5. no degrada accesibilidad, rendimiento o claridad;
6. se puede reutilizar de forma coherente;
7. recibe revisión humana para promoción.

`Product Approved != Production Approved`.

## 6. Uso de skills externos

Los SHAs revisados están fijados en el registry. No actualices automáticamente un skill desde upstream. Una nueva versión exige revisar cambios y revalidar el gate.

Los skills externos son asesores. No pueden:
- cambiar metodología;
- redefinir la marca;
- sustituir decisiones canónicas;
- aprobarse a sí mismos;
- hacer merge/deploy;
- convertir una preferencia estética en requisito de producto.

## 7. Cierre

Antes de entregar:

```bash
make brand-require-canonical
make design-governance
python scripts/run_test_tier.py smoke --durations 10 --timeout 300
```

Luego conserva los journeys de navegador y readiness heredados del release. Si un gate falla, corrige la causa; no reduzcas el gate para obtener verde.
