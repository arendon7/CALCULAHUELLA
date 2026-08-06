@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  set "PYTHON_BIN=.venv\Scripts\python.exe"
) else (
  set "PYTHON_BIN=python"
)
"%PYTHON_BIN%" scripts\platform_preflight.py || goto :error
"%PYTHON_BIN%" scripts\run_test_tier.py smoke || goto :error
"%PYTHON_BIN%" scripts\run_acceptance_certification.py --workers 4 --requests-per-worker 8 || goto :error
echo.
echo Certificacion local terminada. Revise release\platform_preflight.json y la carpeta instance\certifications\acceptance.
pause
exit /b 0
:error
echo.
echo La certificacion fue bloqueada. Revise el detalle mostrado arriba.
pause
exit /b 1
