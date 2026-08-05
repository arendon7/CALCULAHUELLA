# Vista previa web desde GitHub

## Vista pública automática · GitHub Pages

Cada push a `integration/canonical` ejecuta `.github/workflows/pages-preview.yml` y construye un snapshot de:

- landing pública;
- identidad visual y recursos estáticos;
- comportamiento responsive;
- pantalla de acceso;
- runtime ejecutado, release objetivo, rama y commit.

Dirección prevista:

```text
https://arendon7.github.io/CALCULAHUELLA/
```

La primera publicación requiere que GitHub Pages use **Source: GitHub Actions**. Si Pages todavía no está habilitado, el workflow conserva el snapshot como artefacto descargable durante 30 días.

La vista Pages es estática. Formularios y sesión permanecen deshabilitados para no simular operaciones que requieren backend.

## Aplicación completa · GitHub Codespaces

[![Abrir en GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/arendon7/CALCULAHUELLA?ref=integration%2Fcanonical&quickstart=1)

Codespaces ejecuta FastAPI, autenticación, base demo, captura, factores, cálculos, informes, reducción, onboarding, gobierno de release y APIs.

### Abrir

1. Utilizar el botón **Abrir en GitHub Codespaces** o seleccionar `integration/canonical`.
2. Pulsar **Code → Codespaces → Create codespace on integration/canonical**.
3. Esperar a que terminen `postCreateCommand` y `postStartCommand`.
4. GitHub abrirá el puerto **8765**.

Credenciales demo:

```text
consultor@calculatuhuella.local
Demo2026!
```

El puerto se mantiene **Private** por defecto. Para una demostración temporal puede cambiarse a **Public** desde **Ports**. No debe hacerse con datos reales, secretos o evidencias cargadas.

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
CI valida código, migraciones, pruebas y Docker
            ↓
Pages genera/publica landing y login
            ↓
Codespaces permite probar la aplicación completa
```

## Release objetivo

`migration/current-release.json` registra **V1.0.0-RC1** como la última entrega cerrada y validada internamente.

RC1 es una candidata para pilotos y aceptación controlada. No está autorizada como V1.0 productiva. Mientras su ZIP no esté importado, el snapshot mostrará de manera separada:

```text
runtime_version: versión que realmente está ejecutándose
target_release: 1.0.0-rc1
matches_target: false
production_authorized: false
```

Después de importar RC1, `matches_target` podrá ser `true`, pero `production_authorized` seguirá siendo `false` hasta completar pilotos, revisión técnica, Windows 10/11, seguridad independiente, documentos jurídicos e infraestructura productiva real.
