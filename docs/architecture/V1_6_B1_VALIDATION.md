# V1.6-B1 · Validación del corte public marketing

## Estado

**Validado localmente · pendiente de materialización atómica en GitHub**

El parche de referencia se conserva en:

`docs/architecture/patches/V1_6_B1_PUBLIC_ROUTES_VALIDATED.patch`

## Precondición de integridad

La copia local sobre la que se aplicó el corte provenía de la V1.5.5 auditada.

El Git blob SHA de su `app/main.py` antes del cambio fue:

`fb97b56e3f771e7ed6b766840c1aae3c36f80182`

Ese SHA coincide exactamente con el blob de `app/main.py` de la rama `refactor/v1-6-0-consolidation` al diseñar el corte. Por tanto, el diff no se calculó sobre una variante aproximada del monolito.

## Cambio probado

- extraer GET `/` a `app/public_web.py`;
- extraer POST `/contacto` a `app/public_web.py`;
- registrar ambas rutas mediante `register_public_routes(app, templates, current_user)`;
- conservar `current_user` en `main.py` durante B1;
- conservar modelos, tablas, formularios, redirects y semántica.

## Métricas

Antes:

- `app/main.py`: 4.674 líneas;
- rutas decoradas en `app/main.py`: 153.

Después del parche B1:

- `app/main.py`: **4.622 líneas**;
- rutas decoradas en `app/main.py`: **151**;
- `app/public_web.py`: 98 líneas / 2 rutas.

Git blob SHA calculado para el `main.py` modificado:

`b0740e28f56b1a60f41665ad4318d68c82647b3d`

Git blob SHA calculado para `public_web.py`:

`67011bb2d0e712bf15e156d2a766c7ff62b6c725`

## Evidencia de pruebas

### Dirigidas

```text
19 passed in 6.51s
```

Módulos ejecutados:

- `tests/test_v049_landing_windows_factor_dialogue.py`
- `tests/test_v100_rc1_release_candidate.py`

Incluyen la creación de solicitud pública y el redirect esperado:

`/?contacto=recibido#contacto`

### Smoke

```text
56 passed, 426 deselected in 6.35s
```

Comando:

```bash
python scripts/run_test_tier.py smoke --durations 10 --timeout 300
```

## Por qué aún no está aplicado al branch

El conector disponible sustituye archivos existentes como contenido completo y no ofrece patch. `app/main.py` supera 270 KB. La disciplina V1.6 prohíbe reemplazar un archivo de ese tamaño mediante contenido truncable/no verificable.

No se incorporará `public_web.py` como código muerto ni se relajará la barrera arquitectónica para aparentar progreso.

## Condición para materializar B1

Usar una de estas vías:

1. checkout Git exacto + commit normal;
2. herramienta patch confiable;
3. creación de blob completo cuyo SHA pueda verificarse contra `b0740e28f56b1a60f41665ad4318d68c82647b3d` antes de mover el ref.

Hasta entonces, el parche queda validado y reproducible, pero no forma parte del runtime canónico.
