# Estado funcional V0.22

## Clasificación

**Alpha avanzada / prebeta funcional con núcleo metodológico parcialmente formalizado.**

La aplicación es apta para demostraciones, pruebas internas y pilotos controlados. No debe presentarse todavía como plataforma certificada, inventario verificado ni biblioteca metodológica completa.

## Cambio central

V0.22 transforma la metodología de una colección de factores precargados en un sistema con:

- documentos fuente identificados;
- procedencia por versión de factor;
- clasificación de aptitud de uso;
- revisión documental;
- GWP versionados;
- reglas de selección;
- casos patrón reproducibles;
- historial de validaciones.

## Estado de los factores

- **Formal:** factor de emisión UPME del SIN para inventarios 2024.
- **Demostrativos:** factores sintéticos heredados para probar combustibles, transporte, residuos, refrigerantes y otras fuentes.
- **Pendientes:** biblioteca multisectorial Colombia, factores internacionales de respaldo, incertidumbre, biogénico, remociones y factores monetarios.

## Métricas del paquete

- 27 archivos Python.
- 54 plantillas HTML.
- 208 rutas HTTP detectadas.
- 104 pruebas detectadas.
- 15.566 líneas Python.
- 8 documentos metodológicos registrados.
- 6 reglas de selección.
- 8 casos patrón.

## Riesgos abiertos

- El factor formal de electricidad solo representa el SIN y año de datos 2024.
- Los factores demo no pueden migrarse a uso formal únicamente cambiando su estado; requieren fuente primaria y revisión técnica.
- El motor todavía necesita casos patrón para CO₂ biogénico, remociones, año base, incertidumbre, asignación y alcance 2 basado en mercado.
- La biblioteca necesita revisión profesional independiente.
- La deuda de arquitectura, seguridad y piloto real permanece vigente.
