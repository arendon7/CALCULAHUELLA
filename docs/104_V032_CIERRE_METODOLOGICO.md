# V0.32 · Cierre metodológico e incertidumbre

## Objetivo

Cerrar las principales reglas que determinan qué integra el inventario corporativo, qué debe presentarse por separado y qué condiciones deben cumplirse antes de emitir un informe externo.

## Componentes implementados

### 1. Tratamiento contable por fuente

Cada fuente incluida debe clasificarse como:

- Emisión bruta.
- CO2 biogénico informativo.
- Remoción.
- Emisión evitada.
- Compensación.

Solo las emisiones brutas alimentan los totales principales por alcance. Las demás partidas permanecen visibles, trazables y separadas; no se netean automáticamente.

### 2. Alcance 2

Las fuentes de alcance 2 se clasifican como location-based o market-based. La plataforma conserva ambos resultados separados y marca como pendiente cualquier fuente de alcance 2 sin clasificación.

La clasificación market-based no valida por sí sola la calidad de un instrumento contractual. La organización debe documentar su elegibilidad, periodo, mercado, titularidad y ausencia de doble conteo.

### 3. Incertidumbre

Los datos de actividad y versiones de factores pueden registrar incertidumbre porcentual y su fundamento. Por cálculo se aplica:

`u = sqrt(u_dato^2 + u_factor^2)`

La incertidumbre consolidada pondera cada cálculo por sus emisiones y combina las contribuciones por raíz de suma de cuadrados.

La plataforma distingue:

- cobertura de cálculos con incertidumbre;
- cobertura de emisiones brutas;
- fuentes con emisiones pero sin memoria de cálculo de incertidumbre;
- rango inferior y superior únicamente sobre la porción cubierta.

No se presenta un rango parcial como si representara todo el inventario.

### 4. Año base

La política define un umbral porcentual y detonantes de recalculo. Cada evaluación conserva:

- causa;
- total anterior;
- total recalculado;
- variación;
- umbral;
- decisión;
- solicitante, revisor y fecha.

### 5. Puertas metodológicas

El centro metodológico evalúa:

1. política aprobada;
2. clasificación contable;
3. clasificación de alcance 2;
4. incertidumbre completa;
5. casos patrón aprobados;
6. política cuantitativa de año base.

## Informes

Los informes ejecutivo y técnico, y la memoria XLSX, incorporan:

- emisiones brutas;
- CO2 biogénico;
- remociones;
- emisiones evitadas;
- compensaciones;
- alcance 2 dual;
- incertidumbre y cobertura;
- puertas metodológicas;
- partida e intervalo por cálculo.

## Referencias metodológicas priorizadas

- ISO 14064-1:2018.
- GHG Protocol Corporate Standard.
- GHG Protocol Scope 2 Guidance, edición vigente de 2015 mientras culmina su proceso de revisión.
- IPCC 2006 Guidelines y 2019 Refinement, Volumen 1, capítulo de incertidumbre.
- GHG Protocol Land Sector and Removals Standard v1.1, publicado en 2026 y aplicable desde 2027 cuando corresponda.
- Resolución UPME 000085 de 2026 para el factor del SIN 2024, según periodo y uso aplicable.

## Límites

V0.32 implementa gobierno, trazabilidad y cálculos de incertidumbre, pero no sustituye:

- juicio profesional sobre límites y materialidad;
- revisión de la calidad de instrumentos market-based;
- validación de permanencia y titularidad de remociones;
- verificación independiente;
- actualización periódica de factores y estándares.
