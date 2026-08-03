from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path


def check_dependencies() -> None:
    missing: list[str] = []
    for module in ("fastapi", "uvicorn", "jinja2", "sqlalchemy", "multipart", "itsdangerous", "openpyxl", "reportlab", "alembic"):
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    if missing:
        print("\nFaltan dependencias:", ", ".join(missing))
        if os.environ.get("PREFIX", "").endswith("com.termux/files/usr"):
            print("Ejecuta: ./install_termux.sh\n")
        else:
            print("Ejecuta: ./install_mac.sh\n")
        sys.exit(1)


def is_termux() -> bool:
    prefix = os.environ.get("PREFIX", "")
    return "com.termux" in prefix or bool(os.environ.get("TERMUX_VERSION"))


def open_browser(url: str) -> None:
    time.sleep(1.3)
    if os.environ.get("OPEN_BROWSER", "1") != "1":
        return
    if is_termux() and shutil.which("termux-open-url"):
        subprocess.Popen(
            ["termux-open-url", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return
    webbrowser.open(url)


def automation_worker(interval_seconds: int) -> None:
    time.sleep(2)
    from app.automations import process_due_automations
    from app.database import SessionLocal
    while True:
        try:
            with SessionLocal() as session:
                result = process_due_automations(session)
                if result["executed"]:
                    print(f"[Automatizaciones] {result['executed']} ejecutadas · {result['errors']} errores")
        except Exception as exc:
            print(f"[Automatizaciones] Error del programador: {exc}")
        time.sleep(max(15, interval_seconds))


if __name__ == "__main__":
    check_dependencies()
    project_dir = Path(__file__).resolve().parent
    os.chdir(project_dir)

    from app.config import settings
    from app.database import init_db
    from app.operations import diagnostic_snapshot
    import uvicorn

    init_db()
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8765"))
    browser_host = "127.0.0.1" if host == "0.0.0.0" else host
    url = f"http://{browser_host}:{port}/login"

    print(f"\nCalcula tu Huella V{settings.version} · ambiente {settings.environment}")
    print(f"Abre en el navegador: {url}")
    if settings.seed_demo:
        print("Usuario demo: consultor@calculatuhuella.local")
        print("Contraseña: Demo2026!")
    elif settings.bootstrap_admin_email:
        print(f"Administrador inicial: {settings.bootstrap_admin_email}")
    snapshot = diagnostic_snapshot()
    print(f"Base de datos: {snapshot['database_backend']} · estado {snapshot['status']}")
    if settings.is_production and settings.production_issues():
        print("ADVERTENCIA: la configuración productiva tiene requisitos pendientes.")
        for issue in settings.production_issues():
            print(f" - {issue}")
    print("Detener servidor: CTRL + C\n")

    threading.Thread(target=open_browser, args=(url,), daemon=True).start()
    if settings.scheduler_enabled:
        threading.Thread(target=automation_worker, args=(settings.scheduler_interval_seconds,), daemon=True).start()
        print(f"Programador automático: activo cada {settings.scheduler_interval_seconds} segundos")
    try:
        uvicorn.run("app.main:app", host=host, port=port, reload=False, access_log=False)
    except OSError as exc:
        print(f"\nNo fue posible usar el puerto {port}: {exc}")
        print("Prueba con: PORT=8766 ./start_mac.sh\n")
        raise
