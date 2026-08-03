# V0.23 · Biblioteca sectorial y piloto Greenatics

## Objetivo

Pasar del núcleo metodológico general a una aplicación sectorial controlada para tratamiento de residuos orgánicos, biogás y producción de fertilizantes, sin presentar factores pendientes como oficiales.

## Factores incorporados

- Electricidad del SIN para inventarios 2024: UPME, 0,220 kgCO2e/kWh.
- Compostaje en base húmeda: 4 kg CH4/t y 0,24 kg N2O/t.
- Digestión anaerobia en instalación de biogás: 0,8 kg CH4/t en base húmeda.
- Liberación directa de HFC-134a: balance de masa y GWP100 AR6.

Los factores de tratamiento biológico son valores Tier 1 internacionales. Su uso exige verificar aplicabilidad, documentar incertidumbre y preferir mediciones representativas de planta cuando existan.

## Controles de doble conteo

- El factor de CH4 de digestión anaerobia ya considera recuperación de metano.
- El metano recuperado, usado, quemado o venteado debe manejarse mediante balance de planta.
- No debe reportarse dos veces una misma corriente en residuos, aguas residuales y energía.
- Producción de fertilizantes es un indicador de intensidad; no constituye por sí misma una emisión.
- Emisiones evitadas, remociones y compensaciones deben permanecer separadas de las emisiones brutas.

## Piloto Greenatics

La matriz inicial cubre:

- Planta Yarumal.
- Planta Támesis.
- Operación corporativa.
- Alcances 1 y 2.
- Categorías materiales seleccionadas de alcance 3.
- Responsables, unidades, frecuencia, evidencia y preparación del factor.

## Pendientes antes de V1.0

- Parametrización controlada de combustibles FECOC.
- Transporte propio y contratado.
- Aguas residuales con DBO/DQO y tecnología de tratamiento.
- Fertilizantes, aplicación y suelos.
- Otros refrigerantes.
- Incertidumbre cuantitativa por inventario.
- Contraste del piloto contra memoria independiente.
- Revisión metodológica externa.
