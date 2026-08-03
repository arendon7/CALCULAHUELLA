# Plan canónico de migración a GitHub

## Objetivo

Convertir `arendon7/CALCULAHUELLA` en la fuente única de código, ejecución local, pruebas, versiones y despliegues de **Calcula tu Huella**, sin almacenar los ZIP como aplicación ni perder archivos funcionales, recursos visuales, migraciones, pruebas o documentación validada.

## Decisión de línea base

La línea base será **v0.45.5**.

La comparación de los árboles v0.45.2, v0.45.3, v0.45.4 y v0.45.5 confirma que las versiones anteriores no contienen archivos funcionales ausentes en v0.45.5. Sus diferencias exclusivas corresponden a cachés, bytecode o manifiestos históricos. Los documentos de validación anteriores se conservan como trazabilidad.

No se combinarán carpetas ni se copiarán archivos por antigüedad. Cualquier recuperación desde una versión anterior deberá justificarse mediante comparación de contenido y prueba de regresión.

## Principios

1. GitHub almacena el código fuente descomprimido y navegable, no los ZIP de distribución.
2. Los datos locales de usuarios nunca se confirman en Git.
3. La ejecución local debe funcionar desde un `git clone` limpio.
4. Las migraciones Alembic son la autoridad del esquema de base de datos.
5. Los datos de referencia y fixtures demo se versionan; las bases operativas, evidencias y reportes no.
6. Cada etapa se valida antes de fusionarse a `main`.
7. Los ZIP para macOS se generan posteriormente como activos de GitHub Releases.

## Etapa 1 — Inventario y congelamiento

Crear un inventario de la v0.45.5 con:

- ruta relativa;
- tamaño;
- SHA-256;
- tipo de archivo;
- origen;
- decisión: versionar, mover, archivar o excluir.

Verificar como mínimo:

- `app/`;
- `migrations/`;
- `tests/`;
- `docs/`;
- `ops/`;
- `scripts/`;
- recursos estáticos y plantillas;
- Docker, Caddy y configuración;
- scripts e instaladores macOS;
- archivos de metodología, seguridad y producción.

Excluir del árbol canónico:

- `.env` y secretos;
- `instance/*.db`;
- bases SQLite;
- cargas, evidencias y reportes generados;
- respaldos;
- certificados locales;
- logs;
- `.venv`, `__pycache__`, `.pytest_cache` y bytecode;
- ZIP y checksums de distribución.

## Etapa 2 — Importación fuente controlada

Importar la v0.45.5 descomprimida en `migration/v0.45.5`, preservando nombres, contenido y permisos ejecutables.

La primera importación debe mantener la estructura original para facilitar la comparación. No se harán refactorizaciones simultáneas.

Validaciones de importación:

- mismo número de archivos versionables;
- SHA-256 coincidente por archivo;
- recursos PNG/SVG intactos;
- scripts `.sh` y `.command` ejecutables;
- ausencia de datos locales y secretos;
- árbol importado comparable contra el manifiesto fuente.

## Etapa 3 — Estructura del repositorio

Después de validar la importación, ordenar gradualmente el repositorio:

```text
app/                     Aplicación FastAPI
migrations/              Migraciones Alembic
tests/                   Pruebas automatizadas
scripts/
  dev/                   Instalación y ejecución local
  macos/                 Lanzadores e instaladores macOS
  ops/                   Respaldo, restauración y diagnóstico
docs/
  current/               Documentación vigente
  history/               Validaciones y estados anteriores
fixtures/
  demo/                  Datos demostrativos no sensibles
  reference/             Factores, catálogos y datos normativos
packaging/
  macos/                 Fuente de la aplicación e instaladores
ops/                     Infraestructura y operación
.github/workflows/       Integración continua
```

Los cambios de ubicación deben hacerse en commits separados, actualizando rutas y pruebas.

## Etapa 4 — Ejecución local desde GitHub

### Opción Python

El recorrido objetivo será:

```bash
git clone https://github.com/arendon7/CALCULAHUELLA.git
cd CALCULAHUELLA
./scripts/dev/setup.sh
./scripts/dev/run.sh
```

`setup.sh` deberá:

1. verificar Python compatible;
2. crear `.venv`;
3. instalar dependencias;
4. copiar `.env.example` a `.env` cuando no exista;
5. crear directorios locales;
6. ejecutar `alembic upgrade head`;
7. sembrar datos demo solo cuando se solicite;
8. no sobrescribir datos existentes.

`run.sh` deberá iniciar la aplicación y mostrar la URL local.

### Opción Docker

También deberá funcionar:

```bash
docker compose up --build
```

El entorno Docker local utilizará PostgreSQL y volúmenes persistentes. SQLite quedará como alternativa de desarrollo o demostración ligera, no como base productiva.

### Comandos normalizados

Se añadirán comandos equivalentes:

```bash
make setup
make dev
make test
make demo
make reset-demo
make docker-up
make docker-down
```

## Etapa 5 — Datos y persistencia

### Se versiona

- factores y datos metodológicos de referencia;
- catálogos sectoriales;
- plantillas jurídicas y documentales aplicables al producto;
- fixtures demo anonimizados;
- migraciones de esquema;
- semillas necesarias para iniciar la plataforma;
- configuraciones de planes, roles y módulos.

### No se versiona

- bases operativas;
- organizaciones, usuarios o inventarios reales;
- evidencias cargadas;
- documentos generados;
- reportes y certificados emitidos;
- claves, tokens o contraseñas;
- respaldos.

Los datos locales actuales de macOS continuarán en `~/Library/Application Support/CalculaTuHuella`. La migración al repositorio no debe eliminarlos. Los scripts de actualización deberán respaldar, migrar y restaurar esos datos de forma explícita.

## Etapa 6 — Calidad automática

GitHub Actions ejecutará en cada pull request:

1. compilación de Python;
2. validación de sintaxis de scripts;
3. compilación de plantillas Jinja;
4. migración de una base limpia hasta `head`;
5. pruebas unitarias y de integración;
6. pruebas del flujo crítico autenticado;
7. auditoría de secretos;
8. construcción de Docker;
9. verificación del manifiesto de marca y recursos canónicos.

La suite extensa podrá dividirse por dominios para evitar los tiempos excesivos observados en ejecución monolítica.

## Etapa 7 — Pull request y línea estable

La migración se cerrará mediante el PR de `migration/v0.45.5` a `main`.

Antes de fusionar:

- árbol fuente completo importado;
- pruebas verdes;
- ejecución local certificada en una instalación limpia;
- Docker funcional;
- documentación actualizada;
- datos y secretos ausentes;
- comparación contra la v0.45.5 aprobada;
- revisión visual de landing, acceso, dashboard, inventarios, fuentes e importación.

Después del merge:

1. crear etiqueta `v0.45.5-repository-baseline`;
2. crear rama `develop`;
3. continuar cada iteración en `feature/*`;
4. generar instalables desde GitHub Actions/Releases;
5. dejar de usar ZIP como fuente de desarrollo.

## Etapa 8 — Continuación del producto

Una vez consolidado el repositorio, el orden funcional será:

1. reconciliación visual y Marca Maestra;
2. biblioteca de imágenes y web pública;
3. expediente y evidencias;
4. calidad y revisión;
5. cálculo y trazabilidad;
6. informes y aprobación;
7. planes de reducción;
8. piloto Greenatics con datos controlados;
9. endurecimiento de seguridad y despliegue público.

## Criterios de aceptación

La migración se considera terminada cuando:

- un tercero puede clonar el repositorio y ejecutar la aplicación localmente sin usar un ZIP;
- la instalación requiere comandos documentados y reproducibles;
- todas las rutas, plantillas, migraciones y pruebas de v0.45.5 están presentes;
- los recursos visuales canónicos no fueron deformados ni sustituidos;
- la base local existente puede conservarse o migrarse;
- ninguna información operativa o secreta está publicada;
- CI valida cada cambio;
- `main` representa una versión estable y desplegable.

## Entregables de la migración

1. inventario SHA-256 de la fuente;
2. árbol completo importado;
3. `.gitignore` y `.gitattributes` definitivos;
4. scripts `setup`, `run`, pruebas y Docker;
5. documentación de desarrollo local;
6. matriz de comparación contra v0.45.5;
7. CI funcional;
8. PR revisado y fusionado;
9. etiqueta de línea base;
10. primera Release generada desde GitHub.
