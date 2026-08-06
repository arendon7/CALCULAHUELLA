# Guía de producción · Calcula tu Huella V1.0.0

## Uso controlado

La distribución local puede utilizar SQLite para demostraciones y pilotos privados. En esos escenarios debe limitarse el acceso, mantener copias de seguridad y revisar cada inventario antes de divulgarlo.

## Requisitos de producción pública

1. PostgreSQL administrado o con operación documentada.
2. HTTPS y dominios autorizados.
3. Secretos aleatorios fuera del código.
4. Almacenamiento externo para evidencias.
5. Respaldos firmados y réplica fuera del servidor.
6. Ensayo de restauración vigente.
7. SMTP real.
8. Monitoreo, alertas y registros estructurados.
9. Identidad contractual completa.
10. Pruebas Windows cuando se distribuya el instalador local.
11. Revisión de seguridad independiente.

Ejecuta el diagnóstico productivo y no fuerces su aprobación. Los campos de `.env.example` identifican los datos mínimos.

## Configuración jurídica obligatoria

- `LEGAL_PROVIDER_NAME`
- `LEGAL_PROVIDER_NIT`
- `LEGAL_NOTICE_ADDRESS`
- `LEGAL_CONTACT_EMAIL`
- `PRIVACY_CONTACT_EMAIL`
- `LEGAL_EFFECTIVE_DATE`

Los términos, privacidad, DPA, SLA y alcance metodológico se publican desde `/legal/*`.

## Restricciones

- `SEED_DEMO=false`.
- No usar usuarios `@calculatuhuella.local`.
- No usar factores demostrativos en informes formales.
- No divulgar inventarios sin aprobación.
- No afirmar certificación o neutralidad sin proceso específico.
