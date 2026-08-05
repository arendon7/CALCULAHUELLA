# Vista previa web desde GitHub

## Vista pública automática · GitHub Pages

Cada push a `integration/canonical` ejecuta `.github/workflows/pages-preview.yml` y construye un snapshot de:

- landing pública;
- identidad visual y recursos estáticos;
- comportamiento responsive;
- pantalla de acceso;
- runtime ejecutado, release objetivo, rama y commit;
- autorización de despliegue controlado;
- bloqueo de producción pública;
- puertas externas pendientes.

URL:

```text
https://arendon7.github.io/CALCULAHUELLA/
```

GitHub Pages está configurado con workflows. Si el despliegue público falla, el snapshot permanece disponible como artefacto descargable durante 30 días.

La vista Pages es estática. Formularios y sesión permanecen deshabilitados para no simular operaciones que requieren backend.

## Aplicación completa · GitHub Codespaces

[![Abrir en GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/arendon7/CALCULAHUELLA?ref=integration%2Fcanonical&quickstart=1)

Codespaces ejecuta FastAPI, autenticación, base demo, captura, factores, cálculos, informes, reducción, onboarding, gobierno de servicio y APIs.

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

El puerto se mantiene **Private** por defecto. Para una demostración temporal puede cambiarse a **Public** desde **Ports**. No debe hacerse con secretos o evidencias no destinadas a demostración.

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
CI valida código, migraciones, inventario, pruebas y Docker
            ↓
Pages genera/publica landing y login
            ↓
Codespaces permite probar la aplicación completa
```

## Release objetivo

`migration/current-release.json` registra **V1.0.0 FINAL** como la última entrega cerrada para despliegue controlado.

Mientras su ZIP no esté importado, el snapshot muestra por separado:

```text
runtime_version: versión realmente ejecutada
target_release: 1.0.0
matches_target: false
controlled_deployment_authorized: true
public_production_authorized: false
production_authorized: false
```

Después de importar V1.0.0, `matches_target` podrá ser `true`, pero la producción pública continuará bloqueada hasta completar identidad contractual, infraestructura definitiva, Windows 10/11, prueba de penetración independiente, revisión de dependencias externas y aceptación del cliente sobre sus datos.

## Regla de comunicación

No se afirma verificación externa, certificación ISO, neutralidad, carbono negativo ni aseguramiento independiente sin el proceso específico correspondiente.
