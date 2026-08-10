# V1.6.0 · Reconciliación de reporting V1.5.5

## Hallazgo

La rama avanzada de GitHub ya contiene un sistema de reporting sólido, pero la demo local V1.5.5 incorporó mejoras editoriales posteriores que todavía no son canónicas.

La divergencia no está limitada a `app/reporting.py`: las **tres capas documentales** tienen blobs distintos entre GitHub y la baseline local auditada.

## Matriz SHA

| Archivo | GitHub V1.6 | V1.5.5 local auditada | Estado |
|---|---|---|---|
| `app/report_consulting.py` | `e2b4120a8e5589e0593cc6f0aa45d821fbd43c10` | `a5501a5ea45f857acbfd328ee949eb1e1018c3f9` | Divergente |
| `app/report_docx.py` | `ae7a0c4c999dc38dee195b244903c9e976614efa` | `b453d742debcf289a2ce369d5de6654dd636d131` | Divergente |
| `app/reporting.py` | `3c351323a9ac60046b39213526b50e368834ad99` | `c910e54f82383cd0dce3b23cb8b4af87305664cc` | Divergente |

Consecuencia: **C1 no debe portar `reporting.py` en aislamiento**. Primero debe construirse un diff semántico de las tres capas para que PDF, DOCX y narrativa consultiva no terminen comunicando criterios distintos.

## Diferencia ya confirmada en PDF técnico

En `app/reporting.py`, el capítulo remoto de reducción presenta en un párrafo:

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

Portar mejoras como **capa editorial**, no como cambio metodológico.

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

## Corte C0 · diff semántico obligatorio

Antes de escribir código:

1. comparar funciones públicas y helpers de los tres archivos;
2. clasificar diferencias en:
   - dato/cálculo;
   - narrativa;
   - layout/formato;
   - control de calidad;
   - compatibilidad;
3. descartar cualquier cambio local que haya quedado superado por una mejora posterior de GitHub;
4. construir una matriz capítulo → fuente de datos → PDF → DOCX → ejecutivo.

C0 termina cuando exista una lista exacta de bloques a portar y bloques a conservar.

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

### Coherencia tri-formato

C1 debe verificar que la misma interpretación aparezca con profundidad proporcional en:

- narrativa consultiva;
- PDF técnico/ejecutivo;
- DOCX editable.

No se exige idéntica redacción; sí la misma semántica sobre materialidad, calidad, reducción, limitaciones y próximos pasos.

## Tests C1

1. el PDF contiene las cuatro métricas explícitas;
2. los valores provienen del mismo `portfolio` ya usado por la tabla de acciones;
3. DOCX y narrativa usan las mismas magnitudes sin recalcular emisiones;
4. no se recalculan emisiones dentro de reporting;
5. no cambia ningún factor ni fórmula;
6. snapshot/fixture de secciones esperadas;
7. smoke de generación de informe;
8. comparación con reportes sin portafolio o con brecha cero;
9. caso donde cobertura supere 100% sin convertirlo en afirmación de cumplimiento automático.

## Corte C2 posterior

Revisar coherencia editorial avanzada entre:

- informe ejecutivo;
- informe técnico;
- DOCX editable;
- narrativa generada en `report_consulting.py`;
- anexos/artefactos.

Objetivo: una sola semántica con niveles de profundidad distintos según audiencia.

## Regla

Reporting interpreta resultados calculados; **no altera el inventario para que la narrativa sea más conveniente**.
