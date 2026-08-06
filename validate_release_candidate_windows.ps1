Write-Host "Calcula tu Huella V1.0.0 - validacion de version final"
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$python = "python"
if (Test-Path ".venv\Scripts\python.exe") { $python = ".venv\Scripts\python.exe" }
& $python "scripts\validate_release_candidate.py"
Write-Host ""
Write-Host "Para ejecutar toda la regresión: $python -m pytest -q"
