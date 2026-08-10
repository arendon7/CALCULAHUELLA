# V1.6 · CSP3 · Política de estilos

## Estado

**Materializado y validado en `refactor/v1-6-0-consolidation`.**

Commit de materialización: `665055468e5266a158e7072cd3b41d2b8f3b3419`.
Workflow diferencial: `31367091704` — `success`.

## Problema

La política CSP anterior utilizaba `style-src 'self'` como única directiva de estilos. Esa política protegía correctamente los recursos externos, pero también bloqueaba atributos `style="..."` legítimos utilizados por la interfaz.

No se amplió `script-src` ni se habilitó ejecución inline de JavaScript.

## Política materializada

Se conserva:

- `default-src 'self'`;
- `script-src 'self'`;
- `style-src 'self'`;
- `font-src 'self'`;
- `connect-src 'self'`;
- `frame-ancestors 'none'`;
- `base-uri 'self'`;
- `form-action 'self'`.

Se añaden directivas CSP3 específicas:

- `style-src-elem 'self'`: las hojas y elementos de estilo siguen limitados al propio origen;
- `style-src-attr 'unsafe-inline'`: la excepción inline queda limitada a atributos de estilo.

La política contiene una sola aparición de `'unsafe-inline'` y no contiene `'unsafe-eval'`.

## Validación de comportamiento real

Se añadió `tests/test_v160_csp_headers.py`.

La prueba no inspecciona únicamente una constante: abre `/login` mediante `TestClient`, lee el header HTTP `Content-Security-Policy`, lo separa por directivas y exige los valores exactos de `default-src`, `script-src`, `style-src`, `style-src-elem` y `style-src-attr`.

## Gates ejecutados

El workflow `31367091704` aprobó:

1. captura de suite completa baseline;
2. aplicación atómica del cambio;
3. control de alcance: únicamente `app/security.py` y la nueva prueba;
4. `compileall`;
5. barrera arquitectónica;
6. regresión dirigida de seguridad;
7. smoke integral;
8. suite completa diferencial;
9. cero fallos nuevos frente a la baseline;
10. materialización y retiro automático del workflow temporal.

## Decisión de seguridad

No se introducen monkeypatches ni middleware lateral. La excepción necesaria se expresa en la propia CSP y queda acotada a atributos CSS, manteniendo scripts inline y evaluación dinámica bloqueados.

## Gobierno

CSP3 pertenece al PR #19 V1.6.0. El PR permanece en borrador y no implica promoción ni merge a `main`.
