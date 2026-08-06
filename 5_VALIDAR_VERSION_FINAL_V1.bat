@echo off
setlocal
cd /d "%~dp0"
echo Calcula tu Huella V1.0.0 - validacion de version final
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0validate_release_candidate_windows.ps1"
if errorlevel 1 pause
endlocal
