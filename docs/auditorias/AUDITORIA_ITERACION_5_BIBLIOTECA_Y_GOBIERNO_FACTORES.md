# Auditoría Iteración 5 · Biblioteca colombiana y gobierno de factores

**Producto:** Calcula tu Huella  
**Base intervenida:** Iteración 4 · motor metodológico  
**Gobierno de biblioteca:** 1.1.0  
**Alcance:** jerarquía de selección, fuentes colombianas, vigencia, alineación temporal, pasaportes y vigilancia documental.

## 1. Hallazgos previos

La versión base tenía una biblioteca documentada y un asesor de compatibilidad, pero la selección todavía dependía principalmente del puntaje técnico. Faltaban controles explícitos para:

1. diferenciar el orden de preferencia entre evidencia específica, oficial, sectorial, internacional, secundaria y demostrativa;
2. separar documentos oficiales vigentes de resultados preliminares o fuentes en revisión;
3. contrastar sistemáticamente el año representado por el factor con el periodo del dato;
4. impedir que una fuente preliminar se promoviera automáticamente a uso formal;
5. mostrar en la interfaz y exportaciones la jerarquía, estado de fuente y brecha temporal;
6. registrar novedades metodológicas sin crear de inmediato un factor calculable.

## 2. Correcciones implementadas

### 2.1 Jerarquía metodológica

Se incorporó un orden de seis niveles:

1. **Específico verificado:** factor primario de proveedor con verificación y límites comparables.
2. **Oficial nacional:** factor colombiano oficial, pertinente al periodo y al uso.
3. **Sectorial reconocido:** referencia sectorial documentada y aplicable.
4. **Internacional por gas:** IPCC u otra fuente internacional con conversiones y GWP explícitos.
5. **Secundario o piloto:** transcripciones, referencias condicionadas o fuentes que exigen justificación reforzada.
6. **Demostrativo o retirado:** datos sintéticos o no aptos para inventarios formales.

La jerarquía organiza los candidatos, pero no sustituye la aprobación profesional.

### 2.2 Gobierno de fuentes

- Cada pasaporte identifica el estado del documento fuente.
- Las fuentes marcadas como preliminares, borradores, proyectos, consultas o “no incorporadas” bloquean la aptitud formal.
- Se creó un registro de vigilancia para el resultado preliminar del SIN 2025 publicado por XM.
- Ese documento **no genera una versión de factor, no recibe asignaciones y no modifica cálculos**.
- La Resolución UPME 000085 de 2026 permanece como fuente oficial del factor SIN 2024 para inventarios de GEI: 0,220 tCO2e/MWh.

### 2.3 Alineación temporal

Cada versión informa:

- año de referencia del dato;
- año representado por la fuente;
- brecha en años;
- estado: mismo periodo, periodo próximo, requiere justificación, desactualizado o sin año fuente.

Para electricidad se agrega una advertencia específica: debe priorizarse el factor oficial del año del consumo cuando esté disponible.

### 2.4 Biblioteca y pasaportes

La interfaz ahora permite filtrar por:

- nivel de jerarquía;
- alineación temporal;
- aptitud de uso;
- estado de preparación;
- calidad, gas, unidad, geografía, sector y año fuente.

Los pasaportes y tarjetas muestran jerarquía, estado documental, brecha temporal y condición de la fuente.

### 2.5 Registro Colombia y exportaciones

- La biblioteca Colombia diferencia documentos incorporados al cálculo de documentos en vigilancia.
- El Excel de Colombia incorpora hojas de factores, fuentes, casos patrón, limitaciones y gobierno.
- La comparación de factores conserva sus tres hojas históricas y añade columnas de jerarquía, alineación temporal y estado de fuente.
- La API mantiene la versión pública `1.0.0` y añade `governance_version: 1.1.0` para no romper integraciones existentes.

## 3. Fuentes contrastadas

- **UPME, Resolución 000085 de 23 de febrero de 2026:** factor SIN 2024 para inventarios de GEI = 0,220 tCO2e/MWh.  
  https://docs.upme.gov.co/Normatividad/085_2026.pdf
- **UPME, repositorio histórico del factor de emisión del SIN:** conserva resoluciones y soportes por año.  
  https://www.upme.gov.co/simec/oferta-y-demanda/transicion-energetica-justa/cambioclimatico/calculo-del-factor-de-emision-de-co2-del-sin/
- **XM, resultado preliminar del factor de emisión del SIN 2025, 30 de enero de 2026:** incorporado solo como vigilancia documental.  
  https://www.xm.com.co/noticias/8688-resultado-preliminar-del-calculo-de-factor-de-emision-del-sistema-interconectado
- **UPME, calculadora FECOC:** fuente oficial de consulta para factores de emisión de combustibles colombianos.  
  https://app.upme.gov.co/Calculadora_Emisiones1/new/calculadora.html

## 4. Validación ejecutada

- **25 factores y 25 versiones**: no se agregó ni eliminó ninguna versión calculable.
- Recalculo independiente de Iteración 4 e Iteración 5: **200/200 componentes idénticos**.
- Diferencias numéricas encontradas: **0**.
- **6 pruebas nuevas** de gobierno aprobadas.
- Pruebas de páginas, API, pasaportes y exportaciones históricas aprobadas.
- La fuente XM 2025 queda con **0 pasaportes y 0 asignaciones**.
- Código Python compilado y plantillas Jinja validadas.
- Distribuciones Mac y Windows sincronizadas en código, plantillas y pruebas.

## 5. Decisiones de seguridad metodológica

- No se incorporó automáticamente el valor preliminar 2025 al motor.
- No se cambió la asignación oficial de electricidad existente.
- No se modificaron GWP, factores, conversiones, fórmulas ni incertidumbres.
- Una fuente preliminar no puede quedar “Lista para evaluación” aunque su ficha esté completa.
- La obsolescencia temporal genera advertencia; no altera silenciosamente resultados históricos.

## 6. Limitaciones pendientes

- Ampliar la biblioteca oficial colombiana con factores plenamente reproducibles por combustible, tecnología, región y periodo.
- Implementar un flujo formal de propuesta, doble revisión, aprobación, publicación y retiro de cada fuente.
- Evaluar impacto antes de sustituir factores usados en inventarios cerrados.
- Incorporar factores específicos de proveedor y reglas de calidad para instrumentos contractuales de electricidad.
- Completar Scope 3 con categorías, proveedores, asignación y calidad de datos.

## 7. Próxima iteración recomendada

**Iteración 6 · Alcance 3 y gestión de proveedores:** categorías completas, cuestionarios de proveedor, factores específicos, reglas de asignación, materialidad, evidencia y trazabilidad de datos primarios/secundarios.
