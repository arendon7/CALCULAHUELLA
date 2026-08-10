# V1.8 · Climate Disclosure HTTP

## Autoridad

`app/climate_disclosure_web.py` pasa a ser la autoridad HTTP de once contratos para escenarios, declaración climática, requisitos, comité directivo, decisiones y exportaciones XLSX/PDF.

## Dominio preservado

`app/climate_disclosure.py` continúa siendo la autoridad de `scenario_comparison`, `disclosure_summary`, `board_summary` y `build_board_pdf`. No se alteran ponderaciones de escenarios, límites de sensibilidad, score de divulgación, contenido del board pack ni hash documental.

## Gobierno y permisos

La lectura continúa disponible para `view_climate_disclosure` o `manage_climate_disclosure`; las mutaciones exigen `manage_climate_disclosure` y los estados aprobados mantienen la capacidad adicional `approve`. Los registros siguen aislados por organización.

## Gates

Los contratos históricos V0.20 protegen escenarios, límites de supuestos, requisitos, decisiones, XLSX, board pack PDF/hash y duplicados. El contrato V1.8 protege autoridad HTTP, unicidad y permisos.
