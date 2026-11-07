param([int]$Port = 8766, [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$trainingDirectory = $PSScriptRoot
$environmentDirectory = Join-Path $trainingDirectory '.dashboard-venv'
$pythonPath = Join-Path $environmentDirectory 'Scripts\python.exe'
$listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
if ($listener) { throw "Port $Port is already in use. Choose -Port with an available port." }
if (-not (Test-Path -LiteralPath $pythonPath)) {
    $pythonCommand = Get-Command python -CommandType Application -ErrorAction Stop | Select-Object -First 1
    & $pythonCommand.Source -m venv $environmentDirectory
    if ($LASTEXITCODE -ne 0) { throw 'Failed to create dashboard environment.' }
    & $pythonPath -m pip install -r (Join-Path $trainingDirectory 'dashboard\requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Failed to install dashboard dependencies.' }
}
$env:DUCK_DASHBOARD_PORT = "$Port"
Push-Location -LiteralPath $trainingDirectory
try {
    if (-not $NoBrowser) { Start-Process "http://127.0.0.1:$Port" }
    & $pythonPath -m dashboard.server
} finally { Pop-Location }
