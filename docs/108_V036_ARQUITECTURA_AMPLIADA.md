# V0.36 · Arquitectura ampliada por dominios

## Objetivo

Reducir el acoplamiento del controlador principal sin cambiar rutas públicas, permisos, cálculos ni datos históricos.

## Dominios explícitos

1. Organización y sedes: `app/organizations_web.py`.
2. Datos, solicitudes y evidencias: `app/information_web.py`.
3. Revisión y cierre: `app/review_web.py`.
4. Usuarios y membresías: `app/users_web.py`.
5. Inventarios y fuentes: `app/inventories_web.py`.
6. Informes y artefactos: `app/reports_web.py`.
7. Operación y continuidad: `app/operations_web.py`.

## Resultado

- 48 rutas únicas con propiedad explícita.
- Cero duplicados de método y ruta.
- `main.py` reducido de 5.454 a menos de 4.600 líneas.
- Paridad comprobable mediante `/api/arquitectura/resumen`.
- Migración sin cambios de esquema ni recalculo de inventarios.

## Deuda pendiente

La arquitectura aún no está cerrada para V1. Deben separarse dominios avanzados, reducir `database.py`, definir repositorios/servicios y validar despliegue productivo administrado.
