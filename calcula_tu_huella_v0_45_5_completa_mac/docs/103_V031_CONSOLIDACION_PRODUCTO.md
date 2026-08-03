# V0.31 · Consolidación de producto y experiencia

## Decisión de producto

Calcula tu Huella se define como un sistema de gestión de inventarios GEI y descarbonización acompañado por consultoría. La V0.31 no amplía el catálogo funcional: organiza lo existente alrededor del proceso que debe completar el usuario.

## Arquitectura de experiencia

### Vista esencial

1. Inicio y próxima acción.
2. Inventario y fuentes.
3. Datos, evidencias, calidad y cierre mensual.
4. Cálculo, revisión e informes.
5. Análisis y reducción.

### Vista completa

Conserva metodología, Biblioteca Colombia, piloto Greenatics, cadena de valor, escenarios, riesgos, divulgación, operación comercial y administración técnica.

## Perfiles

- Administrador: avance, riesgos, aprobaciones y decisión.
- Consultor: límites, datos, factores, cálculo y entregables.
- Cliente: solicitudes, soportes y calidad de información.
- Revisor: hallazgos, trazabilidad y puertas de aprobación.
- Verificador: paquete reproducible y revisión externa.

## Recorrido único

Configurar → Recolectar → Calcular → Revisar → Reportar.

Cada etapa muestra responsable, condición real, enlace de trabajo y estado. Solo una etapa pendiente se marca como actual.

## Integridad del tablero

La gráfica mensual se calcula desde `ActivityData` y `EmissionCalculation`. Se retiraron la tendencia SVG y la disminución porcentual demostrativas que no provenían del inventario.

## Compatibilidad

No se cambió el esquema de base de datos. La migración actualiza metadatos de versión, conserva inventarios cerrados y mantiene todos los módulos V0.30.
