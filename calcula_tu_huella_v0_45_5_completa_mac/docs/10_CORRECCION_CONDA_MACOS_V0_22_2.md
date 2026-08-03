# Corrección Conda en macOS · V0.22.2

La V0.22.1 suponía que todos los entornos locales tenían `.venv/bin/activate`. Esa suposición es válida para `python -m venv`, pero no para entornos creados con `conda create --prefix`.

V0.22.2 ejecuta siempre el intérprete local mediante `.venv/bin/python`, sin activar el entorno. Esto hace compatibles ambos tipos de entorno y evita interferencias del entorno Conda `base`.

También incorpora selección automática de un puerto libre cuando 8765 está ocupado y un script `stop_mac.sh`.
