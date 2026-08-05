# Política de ingreso de versiones canónicas

## Propósito

Separar cinco decisiones distintas:

1. una versión existe;
2. el paquete fue validado;
3. el runtime fue importado a GitHub;
4. la versión está autorizada para despliegue controlado;
5. la versión está autorizada para producción pública certificada.

Ninguna decisión implica automáticamente la siguiente.

## Rama permanente

Toda integración se realiza en:

```text
integration/canonical
```

Las versiones actualizan `migration/current-release.json`; no crean otra infraestructura ni otra rama principal de migración.

## Estados

### En desarrollo

Falta uno o varios elementos: ZIP cerrado, checksum, manifiesto, validación, inventario, migración reproducible, pruebas, seguridad o activos oficiales.

### Paquete validado pendiente de importación

Existen ZIP, checksum, manifiesto, validación e inventario, pero el binario todavía no se ha ejecutado desde GitHub.

### Runtime canónico importado

El ZIP fue verificado, descomprimido y eliminado; CI pasó y el preview ejecuta la versión objetivo.

### Final para despliegue controlado

Permite demostraciones, pilotos reales acompañados, inventarios internos, contratación privada supervisada y despliegues privados controlados.

### Producción pública certificada

Exige adicionalmente identidad contractual completa, infraestructura definitiva, Windows 10/11, seguridad independiente, revisión de dependencias externas y aceptación del cliente sobre sus datos.

## Puertas de ingreso

Una entrega solo puede gobernar `current-release.json` cuando dispone de:

1. nombre y SHA-256 exactos del ZIP;
2. manifiesto por archivo;
3. validación técnica;
4. documento de decisión o cierre;
5. versión runtime y cabeza Alembic;
6. conteos de rutas, modelos, tablas y plantillas;
7. suite funcional y seguridad;
8. inventario limpio;
9. logos y favicons oficiales;
10. limitaciones y alcance de autorización declarados.

## Puertas de importación GitHub

1. hash exacto del ZIP;
2. extracción segura;
3. tamaños y SHA-256 del inventario;
4. paridad del núcleo Mac/Windows;
5. evidencia final verificada;
6. versión y activos correctos;
7. Alembic desde base vacía;
8. rutas, modelos, tablas y plantillas conforme al contrato;
9. pruebas ejecutadas en procesos aislados;
10. Docker construido;
11. snapshot y Codespaces operativos;
12. ZIP eliminado antes del commit;
13. la autorización pública permanece bloqueada.

## Versión vigente

**V1.0.0 FINAL** es la última entrega cerrada.

Estado:

```text
final_controlled_deployment_validated_pending_binary_import
controlled_deployment_authorized = true
public_production_authorized = false
production_authorized = false
```

## Puertas externas de producción pública

- identidad contractual completa en configuración;
- infraestructura definitiva certificada;
- prueba física en Windows 10;
- prueba física en Windows 11;
- prueba de penetración independiente;
- revisión independiente de dependencias y servicios externos;
- aceptación del cliente sobre sus datos e inventario.

## Regla de comunicación

No se afirmará verificación externa, certificación ISO, neutralidad, carbono negativo ni aseguramiento independiente sin el proceso específico correspondiente.

## Mejoras posteriores

V1.0.0 cierra el ciclo funcional. Los cambios posteriores deben clasificarse como:

- corrección reproducible;
- seguridad;
- accesibilidad;
- rendimiento;
- ajuste derivado de operación controlada;
- precisión metodológica, jurídica o comunicacional;
- preparación verificable para producción pública.

El PR #4 permanece cerrado como antecedente histórico. Cualquier idea útil debe reimplementarse sobre la línea final, no fusionarse desde una versión anterior.
