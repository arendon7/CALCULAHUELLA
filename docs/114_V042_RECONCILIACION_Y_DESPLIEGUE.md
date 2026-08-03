# V0.42 · Reconciliación y despliegue controlado

## Base efectiva

El último paquete completo disponible físicamente al iniciar esta iteración fue V0.37. Los paquetes V0.38–V0.41 estaban descritos en el historial, pero no montados como archivos verificables. V0.42 se construyó sobre V0.37 y materializó las capacidades operativas prioritarias sin afirmar que se recuperó código inexistente.

## Flujo de aprobación

- **Local:** comprueba base, almacenamiento, administrador, auditoría, logs y métricas. PostgreSQL, HTTPS y almacenamiento externo son advertencias.
- **Estricto:** esas dependencias se vuelven críticas. Cada incumplimiento abre o reactiva un incidente deduplicado.

## Persistencia

Se agregaron dos tablas:

- `deployment_rehearsals`;
- `operational_incidents`.

No se modificaron factores, fórmulas, GWP ni cálculos históricos.

## PostgreSQL

La transferencia:

1. exige esquema destino migrado;
2. rechaza destinos con datos;
3. copia siguiendo el orden de dependencias de SQLAlchemy;
4. restablece secuencias PostgreSQL;
5. compara el conteo de todas las tablas dentro de la misma transacción;
6. revierte ante cualquier diferencia.

## Estado de la infraestructura externa

Los archivos Docker y YAML fueron validados sintácticamente. El ensayo vivo sigue pendiente de ejecutarse en un equipo con Docker Desktop; esta limitación permanece visible en la puerta productiva.
