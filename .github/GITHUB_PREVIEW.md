# Vista previa web desde GitHub

## Vista pública automática · GitHub Pages

Cada push a `integration/canonical` ejecuta `.github/workflows/pages-preview.yml` y publica un snapshot de:

- landing pública;
- identidad visual y recursos estáticos;
- responsive;
- pantalla de acceso;
- versión, rama y commit visibles en `preview-status.json`.

Dirección prevista:

```text
https://arendon7.github.io/CALCULAHUELLA/
```

La primera publicación requiere que GitHub Pages esté habilitado con **Source: GitHub Actions** en la configuración del repositorio. Después, cada commit aprobado se publica automáticamente.

La vista Pages es deliberadamente estática. Los formularios y la sesión aparecen deshabilitados para no simular operaciones que requieren backend.

## Aplicación completa · GitHub Codespaces

[![Abrir en GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/arendon7/CALCULAHUELLA?ref=integration%2Fcanonical&quickstart=1)

Codespaces ejecuta FastAPI, autenticación, base demo, formularios, cálculos, informes, reducción, onboarding y APIs.

### Abrir

1. Utilizar el botón **Abrir en GitHub Codespaces**; o seleccionar la rama `integration/canonical`.
2. Pulsar **Code → Codespaces → Create codespace on integration/canonical**.
3. Esperar a que terminen `postCreateCommand` y `postStartCommand`.
4. GitHub abrirá el puerto **8765**.

Credenciales demo:

```text
consultor@calculatuhuella.local
Demo2026!
```

El puerto se mantiene **Private** por defecto. Para una demostración temporal puede cambiarse a **Public** desde la pestaña **Ports**. No debe hacerse con datos reales, secretos o evidencias cargadas.

### Diagnóstico

```bash
bash .devcontainer/start.sh
curl -fsS http://127.0.0.1:8765/api/health
```

Log:

```text
instance/codespaces.log
```

## Flujo de publicación

```text
ChatGPT modifica integration/canonical
            ↓
GitHub registra cada commit
            ↓
CI valida código, migraciones y pruebas
            ↓
Pages publica landing/login automáticamente
            ↓
Codespaces permite probar la aplicación completa
```

## Versión actual

`migration/current-release.json` registra V0.52.0 como la última entrega completa documentada. Mientras el ZIP binario no esté montado e importado, la rama puede seguir ejecutando transitoriamente el runtime anterior; el estado se expone en `preview-status.json` para no confundir versión documentada con versión realmente desplegada.
