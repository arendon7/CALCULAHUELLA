# Núcleo metodológico V0.22

## 1. Objetivo

Mantener separadas cuatro categorías que no deben confundirse:

1. documentos metodológicos;
2. factores de emisión y sus versiones;
3. reglas de selección;
4. validaciones matemáticas del motor.

## 2. Registro de fuentes

Cada documento almacena código, título, emisor, tipo, fecha, jurisdicción, URL, citación, estado, fecha de consulta, notas y campo para checksum SHA-256.

Las fuentes iniciales son:

- GHG Protocol Corporate Standard;
- GHG Protocol Scope 2 Guidance;
- GHG Protocol Scope 3 Standard;
- tabla GWP del GHG Protocol, versión 2.0 de 2024;
- Directrices IPCC 2006;
- Refinamiento IPCC 2019;
- Resolución UPME 000085 de 2026;
- biblioteca interna demostrativa.

## 3. Documentación por factor

Cada versión puede registrar:

- tipo de factor;
- aptitud para reporte;
- página y tabla;
- año del dato;
- valor y unidad original;
- expresión de conversión;
- condición agregada en CO₂e;
- GWP incorporado;
- origen del metano;
- grado de calidad;
- estado de revisión;
- revisor, fecha y restricciones.

## 4. Factor formal inicial

Se incorpora `Electricidad SIN Colombia · inventarios 2024`, versión `UPME-2024-R085`:

```text
0,220 tCO₂e/MWh = 0,220 kgCO₂e/kWh
```

Uso permitido: inventarios corporativos cuando el consumo corresponda al Sistema Interconectado Nacional y se revele que el año del factor es 2024.

Restricción: no confundir con factores para proyectos de mitigación contenidos en la misma resolución.

## 5. GWP

Se almacenan valores AR4, AR5 y AR6 por gas, horizonte de 100 años. Para AR5 y AR6 se diferencia el metano fósil del metano no fósil o asociado a combustión.

## 6. Selección de factores

La selección sigue una jerarquía auditable:

1. factor específico verificado del proveedor;
2. factor oficial nacional pertinente al periodo;
3. factor sectorial reconocido;
4. factor IPCC por gas con conversiones explícitas;
5. factor agregado en CO₂e de uso restringido;
6. bloqueo de datos demostrativos en reportes formales.

La función de candidatos asigna puntajes por actividad, geografía, unidad, aptitud de uso, brecha temporal, calidad y aprobación. El resultado es una recomendación, no una aprobación automática.

## 7. Casos patrón

Los ocho casos iniciales validan:

- electricidad en kWh;
- conversión MWh a kWh;
- CH₄ no fósil AR6;
- CH₄ fósil AR6;
- N₂O AR6;
- toneladas a kilogramos;
- galones estadounidenses a litros;
- rechazo de dimensiones incompatibles.

Cada ejecución conserva versión del motor, ejecutor, fecha, resultado esperado, resultado observado, diferencia absoluta y detalle de fórmula.

## 8. Criterio de uso

Un factor se marca formal únicamente cuando:

- la versión está aprobada;
- existe documentación fuente;
- el uso es `Formal`;
- la revisión documental empieza por `Aprobado`.

Este indicador no sustituye la evaluación de aplicabilidad al inventario concreto.
