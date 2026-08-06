# Auditoría Iteración 7 · Tierras, remociones, carbono biogénico y circularidad

**Fecha:** 5 de agosto de 2026  
**Base:** Iteración 6

## Mejoras implementadas

- Libro mayor persistente para emisiones de cambio de uso del suelo, manejo de tierras, CO₂ biogénico, remociones, reversiones, almacenamiento en productos y beneficios circulares.
- Separación obligatoria: ninguna remoción, almacenamiento o emisión evitada reduce automáticamente las emisiones brutas.
- Controles para remociones: duración del almacenamiento, monitoreo de reversión, ciclo de vida completo, trazabilidad, incertidumbre y fuente metodológica.
- Regla específica para CO₂ biogénico: se reporta como partida informativa; CH₄ y N₂O siguen dentro del alcance aplicable.
- Emisiones evitadas y beneficios circulares solo se registran fuera de los alcances.
- Estados de revisión y auditoría por usuario.
- API y nueva pantalla metodológica.
- Migración Alembic `20260805_0035` validada desde una base vacía.

## Base metodológica

La implementación se alinea con el GHG Protocol Land Sector and Removals Standard v1.0 y la Guidance publicada en junio de 2026. El estándar entra en vigor el 1 de enero de 2027. La versión 1.0 cubre tierras agrícolas productivas y tecnologías de remoción; no cubre todavía la contabilidad forestal general. El almacenamiento de carbono en productos se presenta separadamente de emisiones y remociones.

## Validación

- 4 pruebas específicas de Iteración 7 aprobadas.
- 10 pruebas combinadas de Iteraciones 6 y 7 aprobadas.
- Pruebas metodológicas previas avanzaron sin fallos; la suite histórica conserva el problema conocido de cierre lento por reconstrucción repetida de bases.
- Migración completa hasta `20260805_0035` aprobada.
- Código Python compilado sin errores.
- No se modificaron factores, GWP, conversiones ni funciones de cálculo de emisiones existentes.

## Límites deliberados

- No se generan factores automáticos de suelo o biomasa sin datos y metodología aprobados.
- No se reconoce una remoción como compensación ni como reducción automática del inventario.
- La adicionalidad es un atributo documental, no una aprobación automática.
- La contabilidad forestal integral queda pendiente de la futura guía específica del GHG Protocol.

## Siguiente iteración recomendada

Huella de producto, proyectos de mitigación y verificación independiente.
