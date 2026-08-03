# Corrección del instalador macOS · V0.22.1

## Incidencia corregida

El instalador anterior seleccionaba `python3` sin comprobar su versión. En equipos con macOS o Conda base podía crear `.venv` con Python 3.9. Las dependencias actuales y el código de la aplicación requieren Python 3.11 o superior. La instalación de paquetes fallaba y, como consecuencia, `start_mac.sh` no encontraba Alembic.

## Medidas aplicadas

- Detección explícita de Python 3.11, 3.12 o 3.13.
- Preferencia por binarios versionados antes de `python3`.
- Creación automática de un entorno local Python 3.12 cuando Conda está disponible.
- Eliminación automática únicamente de `.venv` cuando es incompatible.
- Verificación de dependencias antes de ejecutar migraciones.
- Ejecución de Alembic mediante `python -m alembic`.
- Scripts `doctor_mac.sh` y `repair_mac.sh`.
- Mensajes de error accionables.
