# Desarrollo local desde GitHub

## Requisitos

- Python 3.11 o superior.
- Git para clonar el repositorio.
- Docker Desktop opcional para usar PostgreSQL en contenedores.

## Instalación con Python

```bash
git clone https://github.com/arendon7/CALCULAHUELLA.git
cd CALCULAHUELLA
./scripts/dev/setup.sh
./scripts/dev/run.sh
```

La aplicación quedará disponible en:

```text
http://127.0.0.1:8765
```

El instalador crea `.venv`, instala las dependencias, prepara `.env.local`, crea los directorios de ejecución y aplica las migraciones Alembic.

## Comandos normalizados

```bash
make setup       # preparar el entorno
make dev         # iniciar la aplicación
make test        # ejecutar pruebas
make demo        # iniciar con datos demo
make reset-demo  # restablecer la demostración
make docker-up   # iniciar aplicación y PostgreSQL
make docker-down # detener contenedores
```

## Docker y PostgreSQL

```bash
docker compose -f docker-compose.local.yml up --build
```

Los datos se mantienen en volúmenes locales y no se confirman en Git.

## Persistencia macOS

La instalación tradicional para macOS sigue utilizando:

```text
~/Library/Application Support/CalculaTuHuella
```

Clonar o actualizar el repositorio no debe borrar esa información. Antes de migrar una instalación existente, utiliza los scripts de respaldo y restauración incluidos en el proyecto.

## Archivos que no deben publicarse

- `.env` o `.env.local`;
- bases SQLite;
- usuarios, inventarios o evidencias reales;
- reportes y certificados generados;
- respaldos y logs;
- claves, certificados o tokens.
