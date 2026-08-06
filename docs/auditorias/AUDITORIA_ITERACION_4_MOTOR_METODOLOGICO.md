# Auditoría Iteración 4 · Motor metodológico

**Producto:** Calcula tu Huella  
**Base intervenida:** Iteración 3 · usabilidad y formularios  
**Motor de cálculo resultante:** 1.1.0  
**Alcance:** fórmulas, unidades, GWP, factores, incertidumbre y controles de consistencia.

## 1. Diagnóstico previo

La versión base calculaba correctamente los casos demostrativos existentes, pero presentaba riesgos que podían producir resultados materialmente errados al incorporar nuevos factores o configuraciones:

1. La salida de cualquier factor era tratada implícitamente como kilogramos, aunque el campo permitía declarar gramos o toneladas.
2. Las conversiones solo funcionaban cuando existía una relación directa; no resolvían rutas compatibles encadenadas.
3. Una configuración GWP que no identificara AR4, AR5 o AR6 se interpretaba silenciosamente como AR6.
4. Era posible combinar un factor agregado en CO2e con factores desagregados por gas para un mismo dato, con riesgo de doble conteo.
5. El rango de incertidumbre RSS se mostraba como “límite” sin advertir suficientemente los supuestos del Approach 1.
6. La creación y aprobación de factores no impedía que la unidad de salida correspondiera a un gas diferente.
7. No había controles explícitos para valores no finitos en datos, factores, conversiones e incertidumbres.

## 2. Correcciones implementadas

### 2.1 Unidades y conversiones

- Canonización de alias frecuentes como `m3 → m³`, `l → L`, `kwh → kWh` y `ton → t`.
- Conversión directa prioritaria y búsqueda encadenada limitada a cuatro pasos.
- Composición segura de multiplicadores y desplazamientos afines.
- Bloqueo de conversiones entre dimensiones incompatibles.
- Rechazo de resultados no finitos.

### 2.2 Salida de factores

- Normalización obligatoria de la salida a kilogramos del gas declarado.
- Unidades admitidas: `g`, `kg` y `t`, seguidas del gas o de una denominación genérica controlada.
- Verificación de correspondencia entre la unidad y el gas: por ejemplo, un factor N2O no puede declarar `kg CH4`.
- La memoria de cálculo conserva resultado bruto, unidad original y normalización a kg.

### 2.3 GWP y composición de gases

- Eliminación del fallback silencioso a AR6.
- El inventario debe identificar explícitamente AR4, AR5 o AR6 para factores por gas.
- Los factores agregados en CO2e conservan GWP = 1.
- Bloqueo de mezclas CO2e agregado + gases desagregados para el mismo dato.
- Alerta cuando el origen fósil/no fósil del metano no está documentado.
- Alerta cuando un factor agregado no identifica el GWP incorporado.

### 2.4 Vigencia y trazabilidad

- Verificación del periodo del dato frente a `effective_from` y `effective_to` del factor.
- Conservación de alertas por diferencia entre año representado por el factor y año del dato.
- Exclusión de cálculos con estado `Error` de la consolidación por fuente.
- Versión del motor actualizada a **1.1.0** en cálculos y casos patrón.

### 2.5 Incertidumbre

- Validación de porcentajes finitos y no negativos.
- Propagación RSS del dato de actividad y el factor.
- Los resultados se denominan **rangos orientativos**, no intervalos certificados.
- Alerta cuando alguna entrada supera 30 %.
- Nueva puerta metodológica para justificar Approach 2/Monte Carlo cuando existan incertidumbres grandes, asimétricas o correlacionadas.

### 2.6 Gobierno de factores

- La creación de factores rechaza unidades de salida inválidas o incompatibles con el gas.
- La aprobación queda bloqueada si el valor o la salida no son metodológicamente válidos.
- Las conversiones con multiplicadores no finitos o no positivos son rechazadas.

## 3. Referencias contrastadas

- **GHG Protocol · GWP Values v2.0 (2024):** AR6 GWP100 de CH4 no fósil/combustión = 27,0; CH4 fósil fugitivo/proceso = 29,8; N2O = 273.  
  https://ghgprotocol.org/sites/default/files/2024-08/Global-Warming-Potential-Values%20%28August%202024%29.pdf
- **UPME Resolución 000085 de 2026:** factor SIN para inventarios GEI del año 2024 = 0,220 tCO2e/MWh, equivalente a 0,220 kg CO2e/kWh.  
  https://docs.upme.gov.co/Normatividad/085_2026.pdf
- **IPCC 2019 Refinement, Volumen 1, Capítulo 3:** Approach 1 usa propagación simple; requiere revisar correlación, simetría y entradas cercanas o superiores a 30 %, caso en el que Approach 2 puede ser más representativo.  
  https://www.ipcc-nggip.iges.or.jp/public/2019rf/pdf/1_Volume1/19R_V1_Ch03_Uncertainties.pdf

## 4. Validación ejecutada

- **25/25** versiones de factores precargadas compatibles con la normalización de salida.
- Recalculo integral de **4 inventarios**, **25 fuentes** y **200 componentes**.
- **0 errores matemáticos** en los datos demostrativos existentes.
- Comparación Iteración 3 vs. Iteración 4: **0 cambios numéricos** en las 25 fuentes soportadas.
- **8 pruebas nuevas** específicas del motor aprobadas.
- **18 pruebas focalizadas adicionales** aprobadas.
- **147 archivos Python** compilados correctamente.
- **76 plantillas Jinja** validadas.
- Código de aplicación y pruebas idéntico entre Mac y Windows.

## 5. Limitaciones que permanecen

La Iteración 4 fortalece el motor, pero no convierte automáticamente toda la biblioteca en oficial. Permanecen como trabajo posterior:

- ampliar y mantener la biblioteca oficial colombiana por sector, combustible, tecnología y periodo;
- incorporar distribuciones asimétricas y simulación Monte Carlo real;
- reforzar instrumentos contractuales y calidad del dato para Scope 2 market-based;
- desarrollar categorías completas de Scope 3 y reglas específicas por proveedor;
- consolidar remociones, carbono biogénico, tierras y permanencia bajo el estándar correspondiente;
- versionar formalmente cambios de factores y evaluar su impacto sobre inventarios cerrados.

## 6. Próxima iteración recomendada

**Iteración 5 · Biblioteca oficial Colombia y pasaporte de factores:** depuración de factores demostrativos, jerarquía de selección, vigencias, fuentes documentales, cobertura sectorial y controles de aprobación para uso formal.
