# V1.6 · B3 · Contexto de usuario y multiempresa

## Estado

**Materializado y validado en la rama `refactor/v1-6-0-consolidation`.**

Commit de materialización: `7d03127a9f41fc3d1040e3592e2bda0adca67821`.
Workflow de materialización y validación diferencial: `31366342253` — `success`.

## Objetivo

Reducir la concentración de responsabilidades en `app/main.py` sin cambiar el contrato consumido por rutas, dependencias FastAPI ni plantillas.

Antes de B3, `current_user(request)` resolvía en una sola función:

- identidad de sesión;
- usuario activo;
- membresías por organización;
- creación de membresía de compatibilidad cuando no existía ninguna;
- selección y corrección de `active_org_id`;
- rol contextual por organización;
- capacidades por rol;
- modo de vista y perfil;
- proyección de flags `can_*` para UI.

## Implementación

Se creó `app/user_context.py` como autoridad del contexto autenticado.

Responsabilidades separadas:

- `_active_memberships(...)`: obtiene membresías activas y conserva el fallback histórico de membresía primaria;
- `_active_membership(...)`: resuelve la organización activa y restaura la primaria cuando la sesión apunta a una organización no disponible;
- `_capability_flags(...)`: proyecta el conjunto de capacidades al contrato booleano usado por la UI;
- `resolve_current_user(...)`: compone el contexto final del usuario.

`app/main.py` conserva la fachada compatible:

```python
def current_user(request: Request) -> dict[str, object] | None:
    return resolve_current_user(request)
```

No se obliga a reescribir las rutas existentes ni las dependencias `require_user`.

## Invariantes preservados

- el correo de sesión sigue siendo `user_email`;
- usuarios inexistentes o inactivos siguen resolviendo `None`;
- `active_org_id` solo puede seleccionar una membresía activa del usuario;
- una organización activa inválida vuelve a la organización primaria o a la primera membresía válida;
- el rol efectivo proviene de la membresía de la organización activa, no únicamente de `AppUser.role`;
- `ROLE_CAPABILITIES` sigue siendo la autoridad de capacidades;
- se conservan todos los campos y flags `can_*` del contrato anterior;
- no cambia el aislamiento multiempresa ni las rutas HTTP.

## Validación

El workflow `31366342253` ejecutó y aprobó:

1. suite completa de baseline antes del refactor;
2. materialización del servicio y fachada;
3. verificación de alcance de archivos;
4. reducción de concentración en `main.py`;
5. `compileall`;
6. `scripts/audit_architecture.py --enforce`;
7. regresión dirigida de identidad, seguridad, roles, navegación y multiempresa;
8. smoke integral;
9. suite completa posterior comparada contra la baseline;
10. control diferencial de **cero fallos nuevos**.

La baseline completa conserva 11 fallos históricos ya identificados y ajenos a B3. B3 no añade nuevos fallos.

## Pruebas nuevas

`tests/test_v160_user_context.py` cubre explícitamente:

- sesión no autenticada;
- organización primaria y capacidades;
- cambio de rol según membresía de organización activa;
- selección real de una segunda organización;
- rechazo de un `active_org_id` no autorizado y restauración de la organización primaria.

## Resultado arquitectónico

B3 elimina `current_user` de la lista de hotspots extensos de `main.py` y convierte esa función en una fachada estable de dos líneas. La lógica de identidad/tenant queda aislada y testeable sin alterar semántica de producto.

## Gobierno

Este corte pertenece al PR #19 V1.6.0. El PR permanece deliberadamente en borrador y `main` no se fusiona como parte de B3.
