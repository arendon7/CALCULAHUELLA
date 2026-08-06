$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root "install_windows.ps1")
}
$DataRoot = if ($env:CTH_DATA_DIR) { $env:CTH_DATA_DIR } else { Join-Path $env:LOCALAPPDATA "CalculaTuHuella" }
$DbPath = if ($env:CTH_DB_PATH) { $env:CTH_DB_PATH } else { Join-Path $DataRoot "calculatuhuella.db" }
$PidFile = Join-Path $DataRoot "server.pid"
$LogFile = Join-Path $DataRoot "logs\server-windows.log"
$ErrorLogFile = Join-Path $DataRoot "logs\server-windows-error.log"
New-Item -ItemType Directory -Force -Path (Split-Path $LogFile) | Out-Null
if (Test-Path $PidFile) {
    $oldPid = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($oldPid -and (Get-Process -Id $oldPid -ErrorAction SilentlyContinue)) {
        Write-Host "Calcula tu Huella ya esta ejecutandose (PID $oldPid)."
        Start-Process "http://127.0.0.1:8765/"
        exit 0
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}
function Get-FreePort([int]$Preferred) {
    for ($p=$Preferred; $p -le ($Preferred+20); $p++) {
        try { $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback,$p); $listener.Start(); $listener.Stop(); return $p } catch {}
    }
    throw "No hay un puerto disponible entre $Preferred y $($Preferred+20)."
}
$Port = Get-FreePort 8765
$DbUrlPath = $DbPath.Replace('\','/')
$envVars = @{
    CTH_DATA_DIR=$DataRoot; INSTANCE_DIR=$DataRoot; DATABASE_URL="sqlite:///$DbUrlPath";
    APP_ENV="local"; SEED_DEMO="true"; HOST="127.0.0.1"; PORT="$Port"; OPEN_BROWSER="0";
    TRUSTED_HOSTS="localhost,127.0.0.1,testserver"
}
foreach ($entry in $envVars.GetEnumerator()) {
    [System.Environment]::SetEnvironmentVariable($entry.Key, [string]$entry.Value, "Process")
}
$process = Start-Process -FilePath $VenvPython `
    -ArgumentList "run.py" `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $LogFile `
    -RedirectStandardError $ErrorLogFile `
    -WindowStyle Hidden `
    -PassThru
$process.Id | Set-Content $PidFile
$Url = "http://127.0.0.1:$Port/"
for ($i=0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 350
    try { $response = Invoke-WebRequest -UseBasicParsing -Uri "$Url`api/health" -TimeoutSec 2; if ($response.StatusCode -eq 200) { break } } catch {}
}
Write-Host "Calcula tu Huella V1.0.0 esta disponible en $Url" -ForegroundColor Green
Write-Host "PID: $($process.Id) · Datos: $DataRoot"
Start-Process $Url
