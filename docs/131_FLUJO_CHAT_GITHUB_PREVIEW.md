# Flujo continuo ChatGPT → GitHub → Vista previa

## Rama permanente

Toda iteración activa se realiza sobre:

```text
integration/canonical
```

La rama no cambia con cada número de versión. La versión objetivo se registra en:

```text
migration/current-release.json
```

Esto evita ramas V0.49, V0.50, V0.51 y V0.52 compitiendo entre sí.

## Ciclo normal de una iteración

1. Se analiza la necesidad en el chat.
2. Se modifican archivos directamente en `integration/canonical`.
3. Cada unidad coherente recibe un commit descriptivo.
4. GitHub Actions ejecuta CI.
5. GitHub Pages publica landing y login como snapshot estático.
6. Codespaces ejecuta la aplicación completa con backend y datos demo.
7. El PR permanente muestra el conjunto pendiente frente a `develop`.

## Publicación automática

### GitHub Pages

Workflow:

```text
.github/workflows/pages-preview.yml
```

Se ejecuta con cada push a `integration/canonical`. Publica:

- landing;
- login;
- recursos estáticos;
- estado de versión, rama y commit.

Pages sirve para validar diseño, redacción, identidad y responsive. No ejecuta formularios ni autenticación.

### GitHub Codespaces

Configuración:

```text
.devcontainer/
```

Codespaces instala dependencias, migra SQLite demo, inicia FastAPI y expone el puerto 8765. Se utiliza para probar rutas, sesión, formularios, cálculos, informes y APIs.

## Ingreso de una entrega autocontenida

1. `migration/current-release.json` define nombre, hash, conteos y activos.
2. El ZIP se coloca transitoriamente en `migration/inbox/`.
3. `import-current-release.yml` verifica el archivo.
4. `import_current_release.py` instala MAC como runtime canónico.
5. Las diferencias Windows se guardan en `platform/windows/overlay/`.
6. El ZIP se elimina antes del commit automático.
7. CI valida versión, Alembic, rutas, modelos, plantillas, pruebas y Docker.
8. Pages y Codespaces se actualizan desde el mismo árbol.

## Estado transparente

`migration/current-release.json` diferencia:

- versión documentada;
- estado del ZIP;
- runtime importado;
- pendiente de fusión.

La vista Pages expone esta información en:

```text
preview-status.json
```

Nunca se presenta una versión documentada como ejecutada si el binario aún no fue importado.

## Criterio de fusión

La rama se fusiona a `develop` cuando:

- CI está verde;
- Pages fue revisado;
- Codespaces fue probado;
- no existen workflows competidores;
- los activos oficiales están presentes;
- las migraciones son reproducibles;
- no quedan ZIP, bases, secretos, evidencias, logs o cachés;
- el PR es fusionable.

## Regla para versiones futuras

Una versión futura no crea otra infraestructura. Solo cambia `current-release.json` y, cuando sea necesario, las reglas genéricas del importador. Los cambios funcionales continúan acumulándose en `integration/canonical`.
