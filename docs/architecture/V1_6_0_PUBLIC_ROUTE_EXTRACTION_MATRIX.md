# V1.6.0 · Matriz de extracción de rutas públicas/onboarding

## Objetivo

Definir el primer corte real para reducir `app/main.py` sin alterar URLs, sesión, persistencia ni comportamiento visible.

## Bloque candidato

El análisis AST de la baseline V1.5.5 identifica cinco handlers contiguos y de bajo acoplamiento relativo:

| Handler | Método / ruta | LOC | Riesgo | Dependencias principales |
|---|---|---:|---|---|
| `home` | GET `/` | 10 | Bajo | templates, ServicePlan, Session/get_db, current_user |
| `public_contact_request` | POST `/contacto` | 41 | Medio-bajo | CommercialLead, Session/get_db, settings |
| `login_page` | GET `/login` | 5 | Bajo | templates, current_user |
| `login` | POST `/login` | 41 | Medio | AppUser, SessionLocal, login_throttle, password hashing, audit |
| `logout` | POST `/logout` | 3 | Bajo | session |

Total candidato: **100 líneas de handlers** antes de imports/registro.

## Decisión de corte

No extraer las cinco rutas en un único primer commit.

### Corte B1 · public marketing

Extraer primero:
- GET `/`
- POST `/contacto`

Razones:
- no modifica autenticación;
- permite validar el patrón `register_public_routes`;
- reduce riesgo de sesión;
- tiene tests sencillos de paridad HTTP/template/redirect;
- sirve para desacoplar la landing del monolito.

### Corte B2 · auth surface

Después extraer:
- GET `/login`
- POST `/login`
- POST `/logout`

Condiciones adicionales:
- tests de credenciales correctas/incorrectas;
- throttling;
- upgrade de password legacy;
- audit log;
- redirección `next`;
- sesión y rol;
- no-store/CSP/CSRF.

## Firma objetivo

```python
def register_public_routes(
    app,
    templates,
    *,
    get_db,
    current_user,
    common_context,
) -> None:
    ...
```

Para autenticación se prefiere otro registro:

```python
def register_auth_routes(
    app,
    templates,
    *,
    current_user,
    client_ip,
    add_audit,
) -> None:
    ...
```

Separar marketing y auth evita que `public_web.py` se convierta inmediatamente en otro monolito.

## Contratos que no cambian

- `/` sigue siendo la landing pública.
- `/contacto` conserva código de estado/redirección y creación de `CommercialLead`.
- `/login` conserva GET/POST.
- `/logout` conserva POST.
- nombres de templates no cambian.
- nombres de tablas no cambian.
- cookies/sesión no cambian.
- CSP/CSRF no se relajan como consecuencia del refactor.

## Gates B1

1. rutas registradas una sola vez;
2. `/` devuelve 200 y la landing modular;
3. planes activos siguen ordenados por `monthly_fee`;
4. POST `/contacto` válido crea lead;
5. honeypot/timing/validaciones actuales permanecen iguales;
6. smoke;
7. `audit_architecture.py --enforce`;
8. `main_routes` debe **disminuir**, no solo mantenerse.

## Gates B2

Además de B1:
1. login válido;
2. login inválido;
3. bloqueo/throttle;
4. upgrade hash legacy;
5. `next` seguro;
6. logout;
7. audit log;
8. CSRF;
9. cache-control no-store.

## No hacer

- mover `current_user` en el mismo commit;
- cambiar esquema de sesión;
- cambiar hash de contraseñas;
- reescribir la landing;
- alterar ServicePlan;
- introducir un router framework distinto al patrón ya usado por `*_web.py`.

## Resultado esperado de V1.6-B

Después de B1+B2, `main.py` debe perder aproximadamente 100 líneas de handlers y 5 rutas decoradas, con paridad funcional completa. El siguiente corte podrá abordar reporting/reduction usando el mismo patrón.
