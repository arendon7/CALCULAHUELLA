# Producción · V0.45

El entorno demostrativo es opcional y debe permanecer separado de una instalación productiva.

## Reglas

- En producción configure `SEED_DEMO=false`.
- No use las credenciales `@calculatuhuella.local` fuera de demostraciones controladas.
- No presente los valores de Greenatics o Andinas como inventarios oficiales.
- Exija factores aprobados, evidencias reales, revisión independiente y cierre formal antes de divulgar resultados.
- Mantenga la puerta productiva bloqueada hasta validar PostgreSQL, almacenamiento externo, HTTPS, secretos, monitoreo, respaldo y restauración.

La V0.45 puede operar localmente con SQLite para pilotos. La certificación productiva estricta requiere servicios externos realmente conectados.
