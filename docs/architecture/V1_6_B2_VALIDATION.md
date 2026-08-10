# V1.6-B2 · Validación de extracción de autenticación

## Estado

**Validado localmente sobre B1 · pendiente de materialización atómica en GitHub**

Parche:

`docs/architecture/patches/V1_6_B2_AUTH_ROUTES_VALIDATED.patch`

## Alcance

Extraer de `app/main.py`:

- GET `/login`;
- POST `/login`;
- POST `/logout`.

Nuevo módulo objetivo:

`app/auth_web.py`

`current_user` permanece en `main.py` durante B2. No se mezcla resolución multiempresa, capacidades ni sesión activa con la extracción de la superficie de login.

## Resultado acumulado B1+B2

Baseline:

- `main.py`: 4.674 líneas;
- 153 rutas decoradas.

Después de B1+B2:

- `main.py`: **4.569 líneas**;
- **148 rutas** decoradas;
- `public_web.py`: 98 líneas / 2 rutas;
- `auth_web.py`: 103 líneas / 3 rutas.

Git blob SHA del `main.py` acumulado B1+B2:

`10c07bbdcef21cb6e9892b4370163ab880ccbf7a`

Git blob SHA de `auth_web.py`:

`48cf82bbffe86406fc1ab06986c4c1db61d9dbaa`

## Paridad preservada

- login correcto;
- login incorrecto;
- throttle persistente;
- `Retry-After`;
- upgrade de password legacy;
- audit event `LOGIN`;
- sesión `user_email`;
- sesión `active_org_id`;
- redirect de Verificador a `/verificacion`;
- redirect de otros roles a `/dashboard`;
- logout y limpieza de sesión.

## Mejora defensiva incluida

Después de `session.commit()` se copian a escalares locales:

- `organization_id`;
- `role`.

El redirect y la sesión HTTP ya no dependen de leer atributos de un objeto ORM fuera del contexto `SessionLocal`. No cambia el comportamiento externo.

## Evidencia

### Aplicación + seguridad

```text
94 passed in 12.23s
```

Módulos:

- `tests/test_app.py`;
- `tests/test_v024_security_hardening.py`.

### Smoke

```text
56 passed, 426 deselected in 5.38s
```

## No incluido

- mover `current_user`;
- cambiar cookies;
- cambiar `SessionMiddleware`;
- cambiar PBKDF2;
- cambiar CSRF/CSP;
- cambiar RBAC;
- cambiar organización activa;
- cambiar templates de login.

## Siguiente corte de autenticación

Solo después de materializar B1+B2 debe evaluarse un B3 para extraer `current_user`/resolución de contexto de usuario. Ese corte requiere pruebas multiempresa y de cambio de organización activa; no debe mezclarse con login.
