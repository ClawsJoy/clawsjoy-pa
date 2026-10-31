# Start the DEV checkout gateway on 5102 with an isolated data dir.
# Installed PA runs on 5103; dev must never write the installed data.
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root
$env:PA_DATA_DIR = Join-Path $env:LOCALAPPDATA "ClawsJoyPA\data-dev"
$env:CLAWSJOY_DATA_DIR = $env:PA_DATA_DIR
$env:PA_VEC_DIR = Join-Path $env:PA_DATA_DIR "vec"
New-Item -ItemType Directory -Force -Path $env:PA_DATA_DIR, $env:PA_VEC_DIR | Out-Null
Write-Host "[dev] PA_DATA_DIR=$env:PA_DATA_DIR"
Write-Host "[dev] gateway port=5102 (repo config)"
Start-Process -FilePath "python" -ArgumentList "-X","utf8","-B","-u","agent_gateway_enhanced.py" -WorkingDirectory $Root
