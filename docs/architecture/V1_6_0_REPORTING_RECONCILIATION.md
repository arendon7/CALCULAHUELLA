# V1.6.0 · Reconciliación de reporting V1.5.5

## Hallazgo

La rama avanzada de GitHub ya contiene un informe técnico sólido, pero la demo local V1.5.5 incorporó mejoras editoriales posteriores que todavía no son canónicas.

El área más clara de diferencia es el capítulo de reducción y el cierre técnico.

## Estado actual de GitHub

En `app/reporting.py`, el capítulo de reducción presenta en un párrafo:

- reducción requerida;
- reducción estructurada/esperada;
- cobertura;
- brecha;
- preparación del portafolio.

Luego presenta la tabla de acciones.

Los capítulos siguientes se denominan:

- `10. Hallazgos y recomendaciones`;
- `11. Puertas de entrega y limitaciones`;
- `12. Declaración técnica`.

## Mejora validada en V1.5.5

La baseline local auditada mejora esa salida sin cambiar datos, factores ni fórmulas:

1. conserva una narrativa interpretativa de reducción;
2. presenta un cuadro explícito de control con:
   - Reducción requerida;
   - Reducción esperada;
   - Brecha de reducción;
   - Cobertura del portafolio;
3. amplía el capítulo de hallazgos a `Hallazgos, implicaciones y recomendaciones`;
4. amplía gobierno/limitaciones con reglas de uso;
5. cierra con `Declaración técnica y próximos pasos`.

## Decisión V1.6

Portar estas mejoras como **capa editorial**, no como cambio metodológico.

No deben modificarse durante este corte:

- `portfolio['required_reduction']`;
- `portfolio['expected_reduction']`;
- `portfolio['gap']`;
- `portfolio['coverage_percent']`;
- factores de emisión;
- GWP;
- fórmulas;
- cálculos;
- estados de aprobación;
- criterios de release.

## Corte C1 propuesto

### Salida PDF técnica

Agregar una tabla de control antes del detalle de acciones:

| Indicador | Valor | Lectura |
|---|---:|---|
| Reducción requerida | tCO2e/año | Brecha frente a meta/objetivo |
| Reducción esperada | tCO2e/año | Suma estructurada del portafolio |
| Brecha de reducción | tCO2e/año | Diferencia pendiente |
| Cobertura del portafolio | % | Capacidad del portafolio frente al requerimiento |

La columna `Lectura` debe ser descriptiva y no inventar certeza donde no existe.

### Estructura editorial

Renombrar capítulos solo si los contenidos acompañan el cambio:

- Hallazgos → `Hallazgos, implicaciones y recomendaciones`;
- Entrega → `Gobierno de la entrega, limitaciones y uso`;
- Cierre → `Declaración técnica y próximos pasos`.

## Tests C1

1. el PDF contiene las cuatro métricas explícitas;
2. los valores provienen del mismo `portfolio` ya usado por la tabla de acciones;
3. no se recalculan emisiones dentro de reporting;
4. no cambia ningún factor ni fórmula;
5. snapshot/fixture de secciones esperadas;
6. smoke de generación de informe;
7. comparación con reportes sin portafolio o con brecha cero.

## Corte C2 posterior

Revisar coherencia entre:

- PDF técnico;
- informe ejecutivo;
- DOCX editable;
- narrativa generada en `report_consulting.py`;
- `report_docx.py`.

Objetivo: una sola semántica de materialidad, calidad, reducción, limitaciones y próximos pasos, con niveles de profundidad distintos según audiencia.

## Regla

Reporting interpreta resultados calculados; **no altera el inventario para que la narrativa sea más conveniente**.
