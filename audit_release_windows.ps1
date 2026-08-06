param()
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = "python"
if (Test-Path ".venv\Scripts\python.exe") { $python = ".venv\Scripts\python.exe" }
$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("cth-audit-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tempDir | Out-Null

try {
    $env:APP_ENV = "test"
    $env:SESSION_SECRET = "auditoria-local-temporal-v100final"
    $env:DATABASE_URL = "sqlite:///" + (Join-Path $tempDir "auditoria.sqlite3").Replace("\", "/")
    $env:INSTANCE_DIR = Join-Path $tempDir "instance"
    $env:SEED_DEMO = "true"
    $env:OPEN_BROWSER = "0"
    $env:CSRF_ENABLED = "true"
    $env:SCHEDULER_ENABLED = "false"
    $env:STRUCTURED_LOGGING = "false"
    $env:DEPLOYMENT_STRICT = "false"

    Write-Host "============================================================"
    Write-Host "   CALCULA TU HUELLA V1.0.0 - AUDITORIA LOCAL COMPLETA"
    Write-Host "============================================================"

    Write-Host "[1/5] Compilando Python..."
    & $python -m compileall -q app scripts tests run.py
    if ($LASTEXITCODE -ne 0) { throw "Fallo de compilacion Python." }

    Write-Host "[2/5] Aplicando migraciones..."
    & $python -m alembic upgrade head | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Fallo de migraciones." }

    Write-Host "[3/5] Compilando plantillas..."
    & $python -c "from app.main import templates; names=sorted(templates.env.list_templates()); [templates.env.get_template(n) for n in names]; print(f'Plantillas compiladas: {len(names)}')"
    if ($LASTEXITCODE -ne 0) { throw "Fallo de plantillas." }

    Write-Host "[4/5] Ejecutando suite integral reproducible..."
    $collection = (& $python -m pytest --collect-only -q | Out-String)
    $match = [regex]::Match($collection, "(?m)^(\d+) tests collected")
    if (-not $match.Success) { throw "No fue posible determinar el numero de pruebas." }
    $testCount = [int]$match.Groups[1].Value
    $watch = [System.Diagnostics.Stopwatch]::StartNew()
    & $python -m pytest -q
    $watch.Stop()
    if ($LASTEXITCODE -ne 0) { throw "La suite integral fallo." }

    Write-Host "[5/5] Registrando evidencia verificable..."
    $duration = [math]::Round($watch.Elapsed.TotalSeconds, 3).ToString([System.Globalization.CultureInfo]::InvariantCulture)
    & $python scripts\validate_release_candidate.py --record-passed --test-count $testCount --duration-seconds $duration
    if ($LASTEXITCODE -ne 0) { throw "Fallo la validacion final." }

    Write-Host "AUDITORIA APROBADA: $testCount pruebas en $duration segundos."
}
finally {
    Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
}
