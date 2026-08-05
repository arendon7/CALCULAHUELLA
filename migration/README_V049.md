# Antecedente histórico · V0.49.0

Este archivo se conserva únicamente para trazabilidad documental.

V0.49.0 dejó de gobernar la migración, CI, preview y despliegue. No debe utilizarse para cargar una fuente ni para decidir el estado actual del producto.

## Ruta operativa vigente

```text
Rama: integration/canonical
PR permanente: #13
Contrato: migration/current-release.json
Bandeja: migration/inbox/
Workflow: .github/workflows/import-current-release.yml
Release objetivo: V1.0.0-RC1
```

## Herramientas vigentes

```text
scripts/migration/verify_current_release.py
scripts/migration/import_current_release.py
```

Los scripts V0.49 que aún existen son shims de compatibilidad histórica y delegan en las herramientas genéricas.

## Principios que permanecen

- una sola fuente de verdad;
- ZIP como insumo transitorio;
- verificación por SHA-256;
- runtime Mac validado como árbol raíz;
- diferencias Windows como overlay;
- activos oficiales de marca obligatorios;
- migración desde base vacía;
- CI, Docker, Pages y Codespaces desde el mismo árbol;
- importación separada de autorización productiva.

Para cualquier operación actual debe consultarse `migration/current-release.json`.
