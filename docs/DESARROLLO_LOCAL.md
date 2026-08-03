# Desarrollo local desde GitHub

## Requisitos

- Git.
- Python 3.11 o superior; recomendado Python 3.12.
- En macOS, las herramientas de línea de comandos de Xcode.
- Docker Desktop únicamente para la opción con PostgreSQL.

## Instalación con Python y SQLite

```bash
git clone https://github.com/arendon7/CALCULAHUELLA.git
cd CALCULAHUELLA
./scripts/dev/setup.sh
./scripts/dev/run.sh
```

La aplicación queda disponible en `http://127.0.0.1:8765/login`.

La configuración local vive en `.env.local`, que no se confirma en Git. La base SQLite, cargas y reportes se guardan en `instance/`, también excluido del repositorio.

## Usuarios demostrativos

Con `SEED_DEMO=true`, la plataforma crea los usuarios demo definidos por la aplicación. La interfaz de arranque muestra las credenciales vigentes.

## Pruebas

```bash
./scripts/dev/test.sh
```

También se pueden pasar argumentos a pytest:

```bash
./scripts/dev/test.sh tests/test_app.py -q
```

## Docker y PostgreSQL

```bash
docker compose -f docker-compose.local.yml up --build
```

Detener:

```bash
docker compose -f docker-compose.local.yml down
```

Los volúmenes `postgres_local_data` y `app_local_data` conservan los datos locales. Para eliminarlos deliberadamente:

```bash
docker compose -f docker-compose.local.yml down -v
```

## Comandos abreviados

```bash
make setup
make dev
make test
make docker-up
make docker-down
```

## Datos existentes de macOS

La migración al repositorio no elimina ni incorpora automáticamente la información ubicada en:

```text
~/Library/Application Support/CalculaTuHuella
```

Antes de mover información entre instalaciones se debe ejecutar el respaldo y utilizar los scripts de migración correspondientes.
