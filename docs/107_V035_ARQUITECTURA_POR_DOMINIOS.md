# V0.35 · Arquitectura por dominios

## Objetivo

Reducir progresivamente el controlador monolítico sin cambiar rutas, permisos, datos ni resultados.

## Dominios extraídos

| Dominio | Módulo | Rutas |
|---|---|---:|
| Usuarios y membresías | `app/users_web.py` | 4 |
| Inventarios y fuentes | `app/inventories_web.py` | 11 |
| Informes y artefactos | `app/reports_web.py` | 4 |
| Operación y continuidad | `app/operations_web.py` | 5 |

Total: 24 rutas con propiedad explícita.

## Reglas aplicadas

- se conservan los mismos paths HTTP;
- se conservan capacidades y segregación de funciones;
- se mantienen filtros por organización;
- no se trasladan datos ni se recrean tablas;
- la migración es reversible a nivel de esquema porque no agrega columnas;
- la paridad se verifica en tiempo de ejecución.

## Resultado

`main.py` pasó de aproximadamente 5.922 a 5.454 líneas. La deuda arquitectónica permanece abierta porque otros dominios y `database.py` todavía concentran responsabilidades.

## Próxima separación recomendada

1. organización y sedes;
2. información y evidencias;
3. revisión y aprobaciones;
4. servicios de acceso a datos actualmente concentrados en `database.py`.
