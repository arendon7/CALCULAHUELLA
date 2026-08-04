# Vista previa web desde GitHub

## Opción principal: GitHub Codespaces

Codespaces ejecuta la aplicación FastAPI completa, incluida autenticación, base demo, formularios, cálculos, informes y APIs. GitHub Pages no puede ejecutar este backend; únicamente serviría una maqueta estática.

### Abrir

1. Entrar al repositorio en GitHub.
2. Seleccionar la rama `migration/v0.48.0-canonical`.
3. Pulsar **Code → Codespaces → Create codespace on migration/v0.48.0-canonical**.
4. Esperar a que finalicen `postCreateCommand` y `postStartCommand`.
5. GitHub abrirá el puerto **8765** en una nueva pestaña.

Credenciales demo:

```text
consultor@calculatuhuella.local
Demo2026!
```

También están disponibles los perfiles administrador, cliente, revisor y verificador definidos por la semilla demo.

### Estado del puerto

El puerto se mantiene **Private** por defecto. Esto permite compartir la vista únicamente con usuarios autorizados al Codespace.

Para una demostración temporal pública:

1. Abrir la pestaña **Ports** de Codespaces.
2. Ubicar el puerto `8765`.
3. Abrir el menú contextual.
4. Cambiar **Port Visibility** a **Public**.
5. Copiar la URL HTTPS generada.

No debe utilizarse la visibilidad pública con datos reales, secretos o evidencias cargadas.

### Diagnóstico

El servidor escribe:

```text
instance/codespaces.log
```

Para reiniciarlo:

```bash
bash .devcontainer/start.sh
```

Para comprobar salud:

```bash
curl -fsS http://127.0.0.1:8765/api/health
```

## Diferencia con producción

Codespaces es una vista previa efímera. Utiliza SQLite, almacenamiento local y usuarios demo. Una producción estricta requiere PostgreSQL, HTTPS administrado, secretos seguros, almacenamiento externo, monitoreo y restauración comprobada.

## Estado durante la migración

Antes de que Actions importe el ZIP V0.48.0, Codespaces ejecutará temporalmente la base de `develop`. Después del commit automático de importación, debe reconstruirse o recrearse el Codespace para ver la V0.48.0 exacta con sus logos e imágenes oficiales.
