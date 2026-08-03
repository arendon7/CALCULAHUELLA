# V0.34 · Continuidad operativa y arquitectura

## Objetivo

Reducir riesgo operativo y comenzar la separación real del monolito antes de una salida productiva.

## Ensayo de restauración

El control ejecuta cinco puertas:

1. integridad del ZIP;
2. rutas internas seguras;
3. manifiesto y archivo de base coherentes;
4. apertura e integridad de la base restaurada;
5. presencia de las tablas críticas.

El resultado queda persistido en `restore_drills` y se incorpora al diagnóstico `/api/ready`.

## Modularización

Las rutas de operación, respaldos y continuidad fueron retiradas de `app/main.py` y registradas desde `app/operations_web.py`. Es el primer bloque del cierre de `TD-001`; todavía deben extraerse inventarios, usuarios, reportes y administración.

## Criterio de aprobación

V0.34 demuestra que el mecanismo de respaldo es restaurable en un entorno aislado. No demuestra todavía recuperación ante desastre en infraestructura productiva ni reemplaza un plan formal de continuidad.
