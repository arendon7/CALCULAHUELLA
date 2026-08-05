# Bandeja de importación canónica

Esta carpeta recibe temporalmente el ZIP definido en:

```text
migration/current-release.json
```

Entrega actual:

```text
calcula_tu_huella_v1_0_0_final_dual_mac_windows.zip
SHA-256: f6aab6d021e96e8b79bb4f1487db54066c4cd3c8f903d912b97d52e14cdd24c9
```

## Estado

**V1.0.0 FINAL** está cerrada funcionalmente y autorizada para despliegue controlado:

- demostraciones;
- pilotos con datos reales acompañados;
- inventarios internos;
- contratación privada supervisada;
- despliegues privados controlados.

No equivale a producción pública certificada.

Están recuperados y registrados:

- checksum exacto del ZIP;
- manifiesto SHA-256 por archivo;
- validación técnica final;
- acta de cierre funcional;
- aprobación metodológica interna;
- aprobación jurídica interna;
- pilotos internos Greenatics y multisectorial;
- revisión interna de seguridad;
- guías de lanzamiento y producción;
- evidencia automatizada final.

El ZIP binario todavía no está montado en el entorno activo ni presente en esta carpeta. Por eso la importación no se declara ejecutada.

## Contrato final

```text
Runtime: 1.0.0
Rutas: 320
Modelos ORM: 112
Tablas físicas: 113
Plantillas HTML: 76
Alembic: 20260805_0033
Pruebas aprobadas documentadas: 337
Archivos inventariados: 1064
Mac: 534
Windows: 515
```

Evidencia automatizada:

```text
release/FINAL_TEST_EVIDENCE.json
05f9d8ddbc1faca3b891508b9c2166df6b5eb869bf6276e0b6d78479ac5cec4a
```

## Funcionamiento

Cuando aparece el ZIP exacto, `.github/workflows/import-current-release.yml`:

1. verifica nombre y SHA-256 del ZIP;
2. exige `MAC/`, `WINDOWS/` y los documentos finales de gobierno;
3. comprueba tamaño y SHA-256 de cada entrada inventariada;
4. verifica el núcleo compartido y la evidencia final;
5. exige los cuatro activos oficiales de marca;
6. rechaza bases, secretos, evidencias operativas, certificados privados, logs y cachés;
7. usa `MAC/` como runtime canónico;
8. conserva diferencias Windows en `platform/windows/overlay/`;
9. aplica Alembic desde una base vacía;
10. comprueba 320 rutas, 112 modelos, 113 tablas y 76 plantillas;
11. ejecuta cada archivo de pruebas en un proceso aislado;
12. construye Docker;
13. elimina el ZIP antes del commit automático;
14. publica el resultado mediante CI, GitHub Pages y Codespaces.

La importación conserva:

```text
controlled_deployment_authorized = true
public_production_authorized = false
production_authorized = false
```

## Producción pública

Continúa condicionada a:

- identidad contractual completa;
- infraestructura definitiva certificada;
- prueba física en Windows 10 y Windows 11;
- prueba de penetración independiente;
- revisión independiente de dependencias y servicios externos;
- aceptación del cliente sobre sus datos e inventario.

## Versiones futuras

No se crea otra carpeta ni otro workflow. Se actualiza `current-release.json` y se utiliza esta misma bandeja.
