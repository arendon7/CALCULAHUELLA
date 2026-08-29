# Sistema Operativo de Diseño Web · V2.1.1

**Proyecto:** Calcula tu Huella  
**Estado:** contrato de proceso para desarrollo iterativo  
**Fecha:** 11 de agosto de 2026

## Objetivo

Elevar diseño, UX, contenido y calidad de implementación sin introducir una segunda arquitectura paralela. Los skills externos se integran como especialidades dentro de **Binario IA / App Factory**, mientras las decisiones canónicas del proyecto, los quality gates y la autoridad humana conservan precedencia.

La regla operativa es:

> Un skill propone o critica; el sistema del proyecto decide, prueba, registra y gobierna.

## Stack gobernado

| Capa | Fuente principal | Uso |
|---|---|---|
| Producto y arquitectura | Binario IA · Product Lab | necesidad, flujo, arquitectura funcional, escenarios |
| UX de producto | Impeccable + Binario UX System | dashboards, formularios, tablas, tareas, estados |
| Marketing / landing | Taste + Content/Asset Factory | dirección visual, composición, diferenciación |
| Art direction | OpenAI frontend-skill | referencia adicional para composición y jerarquía |
| Motion | Emil Design Engineering | microinteracción, continuidad, feedback y motion |
| Accesibilidad / interacción | Vercel Web Design Guidelines | revisión objetiva de UI |
| UX writing | Binario Content Factory + Vercel Writing Guidelines | títulos, CTA, ayudas, errores, vacíos |
| Componentes | Binario Component Intelligence | descubrir, evaluar, adoptar y reutilizar |
| QA / gobernanza | Binario Quality Gates + journeys del repo | evidencia, regresión y promoción |
| Memoria | Binario Project Memory | decisiones, convenciones, lecciones y anti-patrones |

Los commits upstream revisados están fijados en `WEB_DESIGN_SKILL_REGISTRY.json`. No se siguen ramas `main` de terceros automáticamente.

## Routing por superficie

### 1. Landing y superficies públicas

Orden:

`intención → narrativa → arquitectura de información → assets → dirección visual → responsive → motion → crítica → evidencia`

Taste puede liderar la exploración visual pública. Impeccable hace crítica y pulido. Emil entra después de fijar contenido/layout. La referencia OpenAI sirve como segunda mirada de art direction.

### 2. Aplicación interna

Orden:

`tarea → información necesaria → estados → densidad → interacción → responsive → accesibilidad → evidencia`

Aquí Taste no es controlador primario. Dashboards, formularios, tablas y flujos multietapa se gobiernan con Impeccable, Web Design Guidelines, UX System y Component Intelligence.

Cada pantalla debe optimizar:
- comprensión de estado;
- siguiente acción;
- errores recuperables;
- velocidad de tarea;
- densidad informativa;
- navegación por teclado;
- comportamiento móvil;
- consistencia de componentes.

### 3. Contenido

Content Factory trabaja por pantalla, no como documento aparte. Debe revisar propuesta de valor, títulos, subtítulos, ayudas, CTA, etiquetas, errores, vacíos, onboarding, FAQs y mensajes de sistema dentro de la interfaz real.

### 4. Assets

Asset Factory mantiene:
`necesidad → brief → generación/selección → curaduría → corrección → optimización → naming → alt → manifest → integración`.

Los mockups reales de la aplicación son activos preferentes cuando explican el producto mejor que una ilustración genérica.

### 5. Motion

Motion explica relación, estado o respuesta. Debe ser corto, interrumpible y compatible con `prefers-reduced-motion`. No se añade animación para compensar mala jerarquía.

## Flujo de trabajo mejorado

### Fase A · Entender
1. Product intake y objetivo observable.
2. Revisar implementación real y datos/estados existentes.
3. Recuperar decisiones/memoria relevantes.
4. Clasificar superficie.
5. Definir criterio de éxito y riesgos.

### Fase B · Diseñar
6. Arquitectura de información.
7. Contenido real.
8. Seleccionar/reutilizar componentes.
9. Explorar dirección visual.
10. Prototipar alternativas cuando el cambio sea material.
11. Incorporar assets y motion solo después de la jerarquía.

### Fase C · Criticar
12. Impeccable critique/audit.
13. Web Design Guidelines.
14. Revisión de UX writing.
15. Revisión de motion.
16. Comprobar consistencia contra design system y marca.

### Fase D · Verificar
17. Gate determinista del repo.
18. Smoke/regresión.
19. Desktop + mobile.
20. Teclado/foco.
21. Reduced motion.
22. Vacío/error/alta carga.
23. Journeys reales Playwright.
24. Evidencia visual.
25. Observación de rendimiento y ausencia de layout shift/overflow grave.

### Fase E · Aprender
26. Revisión humana.
27. Si se adopta, registrar decisión/convention/lesson.
28. Si el patrón es reutilizable, pasarlo por Component Intelligence.
29. Solo después continuar el release train normal.

## Quality Gate de diseño

No se aprueba un cambio visible si falta alguno de los gates aplicables:

- `domain_truth_lock`
- `brand_truth_lock`
- `information_architecture`
- `content_quality`
- `accessibility`
- `responsive`
- `motion`
- `browser_e2e`
- `visual_evidence`
- `performance`
- `human_approval`

El gate de diseño complementa, no sustituye, seguridad, arquitectura, migraciones, PostgreSQL, metodología, journeys por rol ni readiness.

## Truth locks

### Dominio
Diseño/UX no modifica factores, GWP, fórmulas, metodología, semántica contable de carbono ni resultados autoritativos.

### Marca
Solo se aceptan los activos clásicos V1.4.2 fijados por hash en el registry y en el manifest de marca. Ningún skill puede redibujar el logo.

### Funcional
Una iteración de diseño no cambia rutas, permisos, contratos de formularios o semántica de negocio salvo un defecto reproducible tratado explícitamente.

## Herramientas de Binario IA que reutilizamos

- Product Intake y Functional Architecture para evitar diseñar antes de entender.
- UX System para estructura, navegación y estados.
- Content Factory y Asset Factory para integrar texto e imagen al producto.
- Mock Data para happy path, vacío, error, roles y alta carga.
- Web Intelligence para inventario/auditoría de superficies y evidencia web.
- Component Intelligence para reutilización con procedencia y QA.
- Model Evaluation para comparar resultados cuando se use IA generativa.
- Project Memory para decisiones y anti-patrones.
- Quality Gates y Governance para fail-closed.
- Version Center/Release Train para no perder una versión buena al crear otra.

## Política de dependencias externas

El repo registra SHAs revisados, pero no vendoriza automáticamente los skills ni los instala en CI. `scripts/design/bootstrap_external_design_skills.sh` es un helper local opcional.

Razones:
- evitar supply-chain drift;
- no hacer que un release dependa de red externa;
- no adoptar cambios upstream sin revisión;
- mantener builds reproducibles.

## Resultado esperado

A partir de este contrato, cada iteración visible debe ser simultáneamente:
- útil;
- clara;
- consistente;
- visualmente cuidada;
- accesible;
- verificable;
- coherente con la marca;
- segura respecto del núcleo metodológico;
- reutilizable cuando corresponda.

La calidad visual deja de depender de una única “inspiración” y pasa a ser un proceso trazable.
