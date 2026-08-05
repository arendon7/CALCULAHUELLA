# Flujo continuo ChatGPT → GitHub → Vista previa

## Rama permanente

Toda iteración activa se realiza sobre:

```text
integration/canonical
```

La rama no cambia con cada versión. La entrega objetivo se registra en:

```text
migration/current-release.json
```

Esto evita ramas y automatizaciones competidoras.

## Ciclo normal de una iteración

1. Se analiza la necesidad en el chat.
2. Se modifica directamente `integration/canonical`.
3. Cada unidad coherente recibe un commit descriptivo.
4. GitHub Actions ejecuta CI.
5. Se genera siempre un snapshot descargable.
6. GitHub Pages publica landing y login cuando está habilitado.
7. Codespaces ejecuta la aplicación completa con backend y datos demo.
8. El PR permanente muestra lo pendiente frente a `develop`.

## Publicación automática

### GitHub Pages

Workflow:

```text
.github/workflows/pages-preview.yml
```

Publica o conserva como artefacto:

- landing;
- login;
- recursos estáticos;
- runtime ejecutado;
- release objetivo;
- rama y commit;
- estado del paquete;
- autorización productiva;
- puertas externas pendientes.

Pages sirve para revisar diseño, redacción, identidad y responsive. No ejecuta formularios ni autenticación.

### GitHub Codespaces

Configuración:

```text
.devcontainer/
```

Codespaces instala dependencias, migra SQLite demo, inicia FastAPI y expone el puerto 8765. Se utiliza para probar sesión, formularios, factores, cálculos, informes, onboarding, gobierno y APIs.

## Ingreso de una entrega autocontenida

1. `current-release.json` define nombre, hash, conteos, evidencia y activos.
2. El ZIP se coloca transitoriamente en `migration/inbox/`.
3. `import-current-release.yml` verifica el archivo.
4. `import_current_release.py` instala `MAC/` como runtime canónico.
5. Las diferencias Windows se guardan en `platform/windows/overlay/`.
6. El ZIP se elimina antes del commit automático.
7. CI valida versión, Alembic, rutas, modelos, tablas, plantillas, evidencia, pruebas y Docker.
8. Pages y Codespaces se actualizan desde el mismo árbol.

## Estado transparente

El contrato diferencia:

- release objetivo;
- runtime ejecutado;
- paquete recibido;
- árbol importado;
- candidata pendiente de aceptación;
- autorización productiva.

La vista expone esta información en:

```text
preview-status.json
```

Nunca se presenta una release como ejecutada si el binario no fue importado. Nunca se presenta una candidata como productiva sin aprobación expresa.

## Release actual

```text
V1.0.0-RC1
runtime: 1.0.0-rc1
scope_frozen: true
production_authorized: false
```

RC1 congela el alcance construido hasta V0.57. Solo admite correcciones, seguridad, accesibilidad, rendimiento, ajustes derivados de pilotos, precisión metodológica o comunicacional y documentación de aceptación.

## Criterio de fusión

La rama puede fusionarse a `develop` cuando:

- el ZIP RC1 fue importado;
- CI está verde;
- Pages fue revisado;
- Codespaces fue probado;
- no existen workflows competidores;
- activos oficiales y evidencia están presentes;
- las migraciones son reproducibles;
- no quedan ZIP, bases, secretos, evidencias operativas, logs o cachés;
- el PR es fusionable.

La fusión a `develop` no autoriza producción.

## Regla para versiones futuras

Una versión futura no crea otra infraestructura. Actualiza `current-release.json` y reutiliza el verificador, importador, CI, Pages, Codespaces y PR permanente.
