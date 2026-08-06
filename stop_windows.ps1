$ErrorActionPreference = "SilentlyContinue"
$DataRoot = if ($env:CTH_DATA_DIR) { $env:CTH_DATA_DIR } else { Join-Path $env:LOCALAPPDATA "CalculaTuHuella" }
$PidFile = Join-Path $DataRoot "server.pid"
if (-not (Test-Path $PidFile)) { Write-Host "No hay un servidor registrado."; exit 0 }
$serverPid = Get-Content $PidFile
$process = Get-Process -Id $serverPid -ErrorAction SilentlyContinue
if ($process) { Stop-Process -Id $serverPid -Force; Write-Host "Servidor detenido (PID $serverPid)." }
else { Write-Host "El proceso ya no estaba activo." }
Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
