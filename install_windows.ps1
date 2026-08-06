$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$DataRoot = if ($env:CTH_DATA_DIR) { $env:CTH_DATA_DIR } else { Join-Path $env:LOCALAPPDATA "CalculaTuHuella" }
$DbPath = if ($env:CTH_DB_PATH) { $env:CTH_DB_PATH } else { Join-Path $DataRoot "calculatuhuella.db" }
$Venv = Join-Path $Root ".venv"
$Python = Join-Path $Venv "Scripts\python.exe"

Write-Host "Calcula tu Huella V1.0.0 - instalacion para Windows" -ForegroundColor Green
Write-Host "Codigo: $Root"
Write-Host "Datos persistentes: $DataRoot"
New-Item -ItemType Directory -Force -Path $DataRoot, (Join-Path $DataRoot "logs"), (Join-Path $DataRoot "backups"), (Join-Path $DataRoot "uploads"), (Join-Path $DataRoot "reports"), (Join-Path $DataRoot "certifications"), (Join-Path $DataRoot "import_staging"), (Join-Path $DataRoot "mail_outbox") | Out-Null

function Find-CompatiblePython {
    $candidates = @()
    if (Get-Command py -ErrorAction SilentlyContinue) { $candidates += ,@("py", "-3.12"); $candidates += ,@("py", "-3.11") }
    if (Get-Command python -ErrorAction SilentlyContinue) { $candidates += ,@("python") }
    if (Get-Command python3 -ErrorAction SilentlyContinue) { $candidates += ,@("python3") }
    foreach ($candidate in $candidates) {
        $exe = $candidate[0]; $args = @(); if ($candidate.Count -gt 1) { $args = $candidate[1..($candidate.Count-1)] }
        try {
            $probe = & $exe @args -c "import sys; print(sys.executable); raise SystemExit(0 if sys.version_info >= (3,11) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) { return @{ Exe=$exe; Args=$args; Path=$probe[-1] } }
        } catch {}
    }
    return $null
}

$rebuild = $false
if (Test-Path $Python) {
    & $Python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)"
    if ($LASTEXITCODE -ne 0) { $rebuild = $true }
}
if ($rebuild -and (Test-Path $Venv)) { Remove-Item -Recurse -Force $Venv }
if (-not (Test-Path $Python)) {
    $candidate = Find-CompatiblePython
    if (-not $candidate) {
        Write-Host "No se encontro Python 3.11 o superior." -ForegroundColor Red
        Write-Host "Instala Python 3.12 desde python.org, activa 'Add Python to PATH' y vuelve a ejecutar este instalador."
        Start-Process "https://www.python.org/downloads/windows/"
        exit 1
    }
    Write-Host "Creando entorno con $($candidate.Path)..."
    & $candidate.Exe @($candidate.Args) -m venv $Venv
}

& $Python -m ensurepip --upgrade | Out-Null
& $Python -m pip install --upgrade pip setuptools wheel
& $Python -m pip install -r (Join-Path $Root "requirements.txt")

$env:CTH_DATA_DIR = $DataRoot
$env:INSTANCE_DIR = $DataRoot
$DbUrlPath = $DbPath.Replace('\','/')
$env:DATABASE_URL = "sqlite:///$DbUrlPath"
$env:APP_ENV = "local"
$env:SEED_DEMO = "true"
& $Python -m alembic upgrade head
& $Python -c "from app.database import init_db; init_db(); print('Base de datos V1.0.0 preparada.')"
& $Python scripts/check_ready.py
Write-Host ""
Write-Host "Instalacion completada." -ForegroundColor Green
Write-Host "Abre 2_ABRIR_CALCULA_TU_HUELLA.bat para iniciar la aplicacion."
