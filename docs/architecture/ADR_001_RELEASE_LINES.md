# ADR-001 · Líneas de desarrollo y release

## Estado

Aceptado para V1.6.0.

## Contexto

El proyecto acumuló varias líneas simultáneas:

- `main` como referencia estable histórica;
- ramas de integración visual y workflow;
- PRs de funcionalidades específicas;
- paquetes Mac autocontenidos V1.5.x construidos fuera de GitHub con mejoras posteriores.

Esta coexistencia permitió iterar rápido, pero volvió ambiguo cuál árbol representa el producto más avanzado y cuál representa una distribución/demo concreta.

## Decisión

A partir de V1.6 se separan tres conceptos.

### 1. Stable baseline

`main` permanece protegido y no recibe cambios de V1.6 hasta que exista una promoción explícita y validada.

### 2. Product development line

`refactor/v1-6-0-consolidation` es la línea de trabajo para reconciliar la funcionalidad avanzada y ejecutar el refactor incremental.

Esta rama parte de `integration/workflow-v1.5.0` porque contiene la evolución funcional más avanzada disponible en GitHub al iniciar el ciclo.

### 3. Distribution/demo release

Los paquetes Mac autocontenidos son artefactos de distribución. Su número de release no redefine automáticamente la versión del núcleo canónico ni autoriza una fusión a `main`.

Las mejoras de un paquete local deben portarse al árbol GitHub con evidencia y tests antes de convertirse en código canónico.

## Reglas

1. No usar números de versión para decidir precedencia funcional.
2. Una superficie más madura no puede ser reemplazada por otra inferior únicamente por provenir de una rama numéricamente posterior.
3. Todo cambio local validado debe reconciliarse explícitamente antes de fusionar.
4. Los PR históricos permanecen como evidencia hasta decidir si se cierran, absorben o retargetean; no se fusionan automáticamente.
5. `main` no se actualiza por arrastre desde una demo local.
6. CI verde es condición necesaria, no autorización suficiente para producción pública.

## Consecuencias

Positivas:

- reduce ambigüedad;
- evita regresiones por precedencia de versiones;
- permite refactor seguro;
- conserva historial de decisiones;
- separa desarrollo de producto de empaquetado Mac.

Costos:

- requiere reconciliación explícita de la V1.5.5;
- obliga a mantener documentación de release más disciplinada;
- algunos PRs históricos deberán cerrarse o retargetearse posteriormente.

## Próxima decisión

Después de reconciliar V1.5.5 en la rama V1.6 se evaluará si:

- PR #17 se retargetea o se cierra como absorbido;
- PR #18 se cierra como absorbido por la nueva landing/handoff;
- `integration/uiux-v1.4.0` permanece únicamente como referencia histórica recuperable.
