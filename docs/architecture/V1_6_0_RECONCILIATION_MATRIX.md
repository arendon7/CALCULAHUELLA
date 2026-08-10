# V1.6.0 · Matriz de reconciliación V1.5.5 → producto canónico

## Propósito

La demo local V1.5.5 acumuló mejoras válidas después de la última línea avanzada publicada en GitHub. Esta matriz evita dos errores opuestos:

1. perder mejoras reales porque solo existieron en el paquete local;
2. convertir decisiones temporales de feria o distribución Mac en deuda permanente del producto.

## Regla de precedencia

Una mejora entra a V1.6 únicamente si cumple simultáneamente:

- pertenece al producto y no solo a la distribución;
- conserva o mejora la seguridad/metodología;
- puede probarse en GitHub;
- no reemplaza una arquitectura más modular por una superficie monolítica;
- no depende de promociones, fechas o condiciones temporales de feria.

## Matriz

| Área | V1.5.5 local | GitHub V1.6 | Decisión |
|---|---|---|---|
| Flujo público | 8 etapas | Reconciliado a 8 etapas | **Portado** |
| Resultados demostrables | Cadena explicable | Ya existe trazabilidad modular; reforzada | **Portado conceptualmente** |
| Landing monolítica Feria | HTML único CSP-safe | Landing modular `public/v14/*` | **No portar como monolito** |
| CSS/JS público | Assets V1.5.x CSP-safe | Autoridad top-level V1.6 | **Consolidado** |
| Precios Feria | Valores promocionales temporales | Soluciones comerciales generales | **No portar al core** |
| Banner Feria Corantioquia | Temporal | No requerido post-evento | **No portar** |
| Modo Feria / reset | Distribución Mac | No pertenece al backend canónico | **Mantener fuera del core** |
| Instalador Mac | backup/staging/rollback | Workflow de distribución | **Portar solo al empaquetado** |
| CSP3 | `style-src-elem 'self'` + `style-src-attr 'unsafe-inline'`; scripts estrictos | CSP anterior | **Pendiente de portar** |
| Árbol de evidencias | `docs/gobierno`, `docs/guias`, `docs/evidencia` | Validadores buscaban raíz antigua | **Portado** |
| Reporting narrativo | Mejor lectura de reducción/gobierno/cierre | Parcialmente anterior | **Pendiente de diff/port selectivo** |
| Marca | Logo clásico canónico | Assets de marca canónicos | **Ya alineado** |
| Reserva verificador/certificador | Explícita | Explícita | **Alineado** |
| Handoff landing→diagnóstico | sector/objetivo, sin PII URL | Contrato V1 con TTL y whitelist | **Portado y validado** |
| Datos demo | 5 organizaciones certificadas | rama workflow contiene entorno demo avanzado | **No convertir demo en semántica productiva** |
| Core version | 1.0.0 | 1.0.0 | **Mantener** |
| Demo/release version | 1.5.5 | V1.6 como ciclo de producto | **Separar conceptos** |

## Estado de reconciliación

### Completado

- gobierno de líneas de release;
- inventario arquitectónico;
- guard para impedir crecimiento de deuda;
- ocho etapas públicas;
- metodología como etapa independiente;
- una sola autoridad JS pública V1.6;
- una sola autoridad CSS pública V1.6;
- árbol documental actual reconocido por `release_candidate.py`;
- árbol documental actual reconocido por `validate_release_candidate.py`;
- eliminación de badge histórico V1.4 de la UI pública;
- preconfiguración sector + objetivo integrada en el parcial modular de la landing;
- contrato `cth_landing_context_v1` / `cth.landing_context.v1` recuperado;
- consumidor con TTL de 30 minutos y whitelist de `sector`/`objective`;
- valores del productor alineados con los selects reales de `/diagnostico`;
- sin PII ni interés comercial en el objeto reutilizable;
- CI canónico verde para el handoff V1.6 en run `31359360758`.

### Pendiente de producto

1. **CSP3**
   - mantener `script-src 'self'`;
   - mantener estilos de hoja en same-origin;
   - permitir atributos de estilo que la UI usa legítimamente para progreso, variables CSS y visualizaciones;
   - añadir test de header real.

2. **Reporting**
   - comparar `app/reporting.py` actual con V1.5.5;
   - portar solo mejoras editoriales/estructurales que no eliminen cambios posteriores;
   - fijar required/expected/gap/coverage en output técnico;
   - seguir `docs/architecture/V1_6_0_REPORTING_RECONCILIATION.md`.

3. **Empaquetado Mac**
   - llevar backup/staging/rollback al workflow de artefactos cuando el core V1.6 esté estable;
   - no mezclar scripts `Modo Feria` con la app productiva.

## Activos de compatibilidad temporal

Los siguientes archivos pueden permanecer durante V1.6-A aunque ya no sean cargados por `public_base.html`:

- `app/static/js/public-v1.4.js`
- `app/static/css/public-v1.4.css`
- `app/static/css/v14-public/*`

Política:

- `public-v1.4.js` y `public-v1.4.css` quedan **deprecados** y no deben recibir nuevas funciones;
- `v14-public/*` se mantiene como implementación parcial interna detrás del agregador `public-v1.6.css`;
- retirar archivos top-level V1.4 solo después de verificar cero consumidores en tests, templates, Pages y workflows;
- renombrar siete parciales por estética no es prioridad mientras exista deuda funcional más importante.

## Qué no debe regresar

- precios/promociones Feria dentro del core;
- versiones visibles de implementación como argumento comercial;
- HTML público monolítico con CSS/JS inline;
- doble autoridad JS o CSS;
- evidencia duplicada en raíz para satisfacer validadores antiguos;
- afirmaciones de verificación/certificación automáticas;
- decisión de precedencia basada únicamente en número de versión.

## Criterio de cierre de reconciliación

La reconciliación V1.5.5 se considera terminada cuando CSP y reporting estén portados/verificados, y la línea V1.6 pueda generar una demo equivalente o superior sin depender de archivos locales fuera de GitHub.
