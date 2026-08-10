# V1.6 · Methodology / Calculation Boundary · Methodology Administration

## Corte

Las cuatro rutas administrativas históricas de metodología pasan a `app/methodology_admin_web.py`:

- `GET /metodologia`;
- creación de factor;
- cambio de estado de versión de factor;
- creación/actualización de conversión.

Los módulos especializados `methodology_web.py`, `factor_library_web.py` y `methodology_closure_web.py` permanecen intactos.

## Regla crítica

El corte es de **propiedad HTTP**. `normalize_factor_output`, modelos, valores GWP, motor de cálculo, conversiones persistidas y reglas de aprobación conservan su implementación previa.

## Contratos

1. Cuatro rutas únicas y operativas.
2. Unidad no autorizada sigue devolviendo HTTP 400.
3. Conversión entre dimensiones incompatibles sigue bloqueada.
4. El rol Cliente continúa sin acceso a `/metodologia`.
5. Suite completa, arquitectura y smoke verdes antes del commit.
