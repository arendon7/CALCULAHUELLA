# Flujo continuo ChatGPT → GitHub → Vista previa

## Rama permanente

Toda mejora activa se realiza sobre:

```text
integration/canonical
```

La entrega objetivo se registra en:

```text
migration/current-release.json
```

## Ciclo de trabajo

1. Se analiza la necesidad en el chat.
2. Se modifica `integration/canonical`.
3. Cada unidad coherente recibe un commit descriptivo.
4. GitHub Actions ejecuta CI.
5. Se genera un snapshot descargable.
6. GitHub Pages publica landing y login.
7. Codespaces ejecuta la aplicación completa.
8. El PR permanente muestra lo pendiente frente a `develop`.

## Superficies de revisión

### GitHub Pages

Workflow:

```text
.github/workflows/pages-preview.yml
```

Expone:

- landing;
- login;
- recursos estáticos;
- runtime ejecutado;
- release objetivo;
- rama y commit;
- autorización de despliegue controlado;
- bloqueo de producción pública;
- puertas externas pendientes.

### GitHub Codespaces

Configuración:

```text
.devcontainer/
```

Ejecuta FastAPI, sesión, formularios, factores, cálculos, informes, onboarding, gobierno y APIs en el puerto 8765.

## Ingreso de una entrega autocontenida

1. `current-release.json` define nombre, hash, conteos, evidencia y activos.
2. El ZIP se coloca transitoriamente en `migration/inbox/`.
3. `import-current-release.yml` verifica identidad e inventario.
4. `import_current_release.py` instala `MAC/` como runtime canónico.
5. Las diferencias Windows se guardan en `platform/windows/overlay/`.
6. El ZIP se elimina antes del commit automático.
7. CI valida versión, migraciones, rutas, modelos, tablas, plantillas, evidencia, pruebas y Docker.
8. Pages y Codespaces se actualizan desde el mismo árbol.

## Estado transparente

`preview-status.json` diferencia:

- runtime realmente ejecutado;
- release objetivo;
- coincidencia entre ambos;
- despliegue controlado autorizado;
- producción pública bloqueada;
- puertas externas pendientes.

Nunca se presenta una release como ejecutada si el binario no fue importado. Nunca se presenta un despliegue controlado como producción pública certificada.

## Release actual

```text
V1.0.0 FINAL
runtime objetivo: 1.0.0
controlled_deployment_authorized: true
public_production_authorized: false
production_authorized: false
```

V1.0.0 cierra el ciclo funcional y puede utilizarse para demostraciones, pilotos acompañados, inventarios internos, contratación privada y despliegues privados supervisados.

## Criterio de fusión a `develop`

- ZIP V1.0.0 importado y eliminado antes del commit;
- CI verde;
- inventario SHA-256 verificado;
- runtime `1.0.0`;
- 320 rutas, 112 modelos, 113 tablas y 76 plantillas;
- Alembic `20260805_0033` desde base vacía;
- evidencia final válida;
- logos y favicons oficiales;
- Pages revisado;
- Codespaces probado;
- overlay Windows generado;
- ningún ZIP, base, secreto, evidencia operativa, log o caché en Git;
- PR fusionable.

La fusión a `develop` no autoriza producción pública.

## Trabajo posterior a V1.0.0

Solo se incorpora como:

- corrección reproducible;
- seguridad;
- accesibilidad;
- rendimiento;
- ajuste derivado de operación controlada;
- precisión metodológica, jurídica o comunicacional;
- preparación verificable para producción pública.
