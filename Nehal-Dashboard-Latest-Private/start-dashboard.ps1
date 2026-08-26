$projectDir = $PSScriptRoot
$pythonExe = 'C:\Users\ORIGINAL\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$pnpmExe = 'C:\Users\ORIGINAL\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\fallback\pnpm.cmd'

if (-not (Test-Path -LiteralPath $pythonExe)) { Write-Error 'Python runtime was not found.'; Read-Host; exit 1 }
if (-not (Test-Path -LiteralPath $pnpmExe)) { Write-Error 'pnpm runtime was not found.'; Read-Host; exit 1 }

$backend = "Set-Location -LiteralPath '$projectDir\backend'; & '$pythonExe' -m alembic upgrade head; if (`$LASTEXITCODE -eq 0) { & '$pythonExe' -m uvicorn app.main:app --reload --port 8000 }"
$frontend = "Set-Location -LiteralPath '$projectDir\frontend'; & '$pnpmExe' run dev -p 3100"

function Test-DashboardUrl([string]$url) {
    try { $null = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2; return $true } catch { return $false }
}

if (-not (Test-DashboardUrl 'http://127.0.0.1:8000/health')) {
    Start-Process powershell.exe -WindowStyle Hidden -ArgumentList '-NoExit','-NoProfile','-Command',$backend
}
if (-not (Test-DashboardUrl 'http://127.0.0.1:3100/login')) {
    Start-Process powershell.exe -WindowStyle Hidden -ArgumentList '-NoExit','-NoProfile','-Command',$frontend
}

$ready = $false
for ($attempt = 0; $attempt -lt 60; $attempt++) {
    if ((Test-DashboardUrl 'http://127.0.0.1:8000/health') -and (Test-DashboardUrl 'http://127.0.0.1:3100/login')) { $ready = $true; break }
    Start-Sleep -Seconds 1
}
if (-not $ready) { Write-Warning 'The dashboard is still starting. Check the two service windows for details.' }
Start-Process 'http://127.0.0.1:3100'
