# V0.33 · Piloto Greenatics controlado

## Objetivo

Convertir el piloto Greenatics en una ejecución verificable y no únicamente en un inventario con total anual.

## Unidades operativas

- Planta Yarumal.
- Planta Támesis.
- Operación corporativa Medellín.

## Controles incorporados

1. **Cobertura por frecuencia:** compara periodos cargados contra los esperados para cada fuente.
2. **Cobertura mensual:** muestra por sede los registros presentes y faltantes para fuentes mensuales.
3. **Evidencia:** exige soportes vinculados; un dato sin evidencia no habilita la aprobación.
4. **Factores:** conserva asignación únicamente de versiones aprobadas.
5. **Contraste por fuente:** registra resultado de la memoria independiente, diferencia absoluta, variación y estado.
6. **Incidencias:** documenta causas, responsables, vencimientos y resolución.
7. **Aprobación:** permanece bloqueada mientras exista cualquier puerta crítica pendiente.

## Umbral de contraste

Una fuente se considera conforme cuando la diferencia relativa frente a la memoria independiente es menor o igual al 2%. La conformidad agregada exige cobertura del 100% de las fuentes vinculadas.

## Contexto operativo

La versión muestra algunos datos operativos aportados por Greenatics —capacidades y acumulados conocidos— únicamente como referencia. No se crean registros de actividad ni cálculos sin distribución temporal, unidad, soporte y aprobación.

## Plantilla Excel

La plantilla de ejecución contiene:

- control de ejecución;
- fuentes vinculadas;
- datos mensuales;
- contraste por fuente;
- cobertura mensual;
- contexto operativo;
- incidencias.

## Criterio de salida

El piloto solo puede aprobarse cuando:

- todas las fuentes tengan la frecuencia esperada completa;
- exista evidencia por fuente;
- los factores aplicables estén aprobados;
- el contraste por fuente cubra el 100%;
- las diferencias sean conformes o estén corregidas;
- no existan incidencias altas o críticas abiertas.
