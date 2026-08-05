# Política de ingreso de versiones canónicas

## Propósito

Evitar cambios repetidos de base por iteraciones todavía en desarrollo y separar cuatro decisiones distintas:

1. una versión existe;
2. el paquete fue validado;
3. el runtime fue importado a GitHub;
4. la versión está autorizada para producción.

Ninguna de estas decisiones implica automáticamente la siguiente.

## Rama permanente

Toda integración se realiza en:

```text
integration/canonical
```

Las versiones futuras actualizan `migration/current-release.json`. No crean otra infraestructura ni otra rama principal de migración.

## Estados

### En desarrollo

Existe código o una iteración activa, pero falta uno o varios elementos:

- ZIP cerrado;
- SHA-256;
- manifiesto;
- validación;
- inventario de archivos;
- migración desde base vacía;
- pruebas funcionales y de seguridad;
- activos visuales completos.

No reemplaza el contrato canónico.

### Paquete validado pendiente de importación

Existen ZIP, checksum, manifiesto, validación e inventarios, pero el binario todavía no se ha importado y ejecutado en GitHub.

### Runtime canónico importado

El ZIP fue verificado, descomprimido y eliminado; CI pasó y la vista previa ejecuta la versión objetivo.

### Candidata de lanzamiento

El runtime está técnicamente congelado y dispone de gobierno de release. Puede utilizarse para pilotos y aceptación controlada, pero no se presenta como producción.

### Autorizada para producción

Solo procede con evidencia externa completa, defectos críticos y altos resueltos o decididos formalmente, e infraestructura productiva certificada.

## Puertas de ingreso

Una entrega solo puede gobernar `current-release.json` cuando se dispone de:

1. nombre exacto del ZIP;
2. SHA-256 del ZIP;
3. manifiesto;
4. validación técnica;
5. versión runtime coherente;
6. cabeza Alembic;
7. conteo de rutas, modelos, tablas y plantillas;
8. suite funcional y seguridad;
9. inventario sin bases, secretos, evidencias operativas, logs ni cachés;
10. logos y favicons oficiales;
11. árboles o inventarios verificables por plataforma;
12. limitaciones declaradas.

## Puertas de importación GitHub

1. hash exacto del ZIP;
2. extracción segura;
3. paridad del núcleo Mac/Windows;
4. evidencia interna verificada por SHA-256;
5. versión y activos correctos;
6. Alembic desde base vacía;
7. rutas, modelos, tablas y plantillas conforme al contrato;
8. archivos de pruebas ejecutados en procesos aislados;
9. Docker construido;
10. snapshot y Codespaces operativos;
11. ZIP eliminado antes del commit;
12. `production_authorized` permanece sin alteración automática.

## Puertas de producción

Una importación o fusión nunca autoriza producción por sí sola. La autorización exige evidencia de:

- pilotos definidos;
- revisión técnica independiente de la construcción;
- instalación real en sistemas soportados;
- seguridad independiente;
- documentos jurídicos y contractuales;
- infraestructura real de datos, objetos, correo, DNS, TLS, secretos, monitoreo y restauración;
- aprobación formal de salida.

## Versión vigente

**V1.0.0-RC1** es la última entrega cerrada y validada internamente.

Estado:

```text
release_candidate_validated_pending_binary_import
production_authorized = false
```

La candidata congela el alcance funcional construido hasta V0.57. Durante RC1 solo se admiten defectos reproducibles, seguridad, accesibilidad, rendimiento, ajustes de piloto, precisión metodológica o comunicacional y documentación de aceptación.

## Reconciliación de mejoras paralelas

El PR #4 se conserva como inventario histórico. Después de importar RC1 se compara por capacidad. Solo se porta aquello que:

- no esté ya presente;
- no retroceda la versión;
- no sustituya activos oficiales;
- respete el alcance congelado;
- no cambie metodología sin decisión explícita;
- conserve seguridad, pruebas y trazabilidad.
