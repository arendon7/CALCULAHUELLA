# Calcula tu Huella V1.0.0 · cierre y liberación

## Decisión de producto

La V1.0.0 congela el alcance funcional desarrollado hasta V0.57 y cierra el ciclo de ampliación. A partir de esta versión solo se admiten correcciones, actualizaciones metodológicas documentadas, seguridad, compatibilidad e infraestructura.

## Aprobaciones incorporadas

1. **Metodología:** Carlos Uribe aprueba internamente el diseño del flujo, controles, trazabilidad y limitaciones.
2. **Jurídica:** Agustín Rendón aprueba la base contractual y de privacidad para despliegue controlado.
3. **Piloto Greenatics:** recorrido funcional multisede y sector residuos validado con datos demostrativos.
4. **Piloto multisectorial:** servicios, industria y agro validados para evitar sobreajuste.
5. **Seguridad interna:** controles aplicables revisados con referencia a OWASP ASVS.
6. **Regresión:** evidencia automatizada distribuida dentro de `release/FINAL_TEST_EVIDENCE.json`.

## Clasificación de la liberación

### V1.0 final · despliegue controlado

Autoriza:
- demostraciones;
- pilotos acompañados;
- contratación privada;
- inventarios internos;
- informes revisados profesionalmente;
- despliegues privados con configuración segura.

### Producción pública

Permanece condicionada a:
- NIT, domicilio y correos contractuales configurados;
- PostgreSQL, TLS, almacenamiento, SMTP, monitoreo y respaldos reales;
- restauración certificada;
- prueba física en Windows 10 y 11;
- prueba de seguridad independiente;
- aceptación de datos e inventario por cada cliente.

## Regla de mantenimiento

No se incorporarán capacidades nuevas a V1.0 sin abrir un ciclo de producto posterior. Las correcciones se versionarán como V1.0.x.
