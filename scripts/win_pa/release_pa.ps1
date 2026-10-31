# Release PA payload/installer with the installed-app dedicated port.
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\win_pa\release_pa.ps1
#   ... -SkipInstaller
# The port is deliberately NOT inherited from the dev config: dev stays 5102,
# installed payload is 5103 (build-time rewrite of payload config only).
param(
  [string]$Ref = "HEAD",
  [string]$Out = "dist\pa_shell\payload",
  [switch]$SkipInstaller
)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root
$env:PYTHONIOENCODING = "utf-8"
$Port = 5103
Write-Host "[release] payload ref=$Ref out=$Out installedPort=$Port"
python -X utf8 -B scripts\win_pa\make_payload.py --ref $Ref --out $Out --go --gate --force --gateway-port $Port
if ($LASTEXITCODE -ne 0) { throw "payload failed rc=$LASTEXITCODE" }
$pl = Join-Path $Root "dist\pa_shell\payload\scripts\win_pa\port_lite.py"
$py = Join-Path $Root "dist\pa_shell\payload\runtime\python.exe"
$got = & $py $pl --root (Join-Path $Root "dist\pa_shell\payload")
if ([int]$got -ne $Port) { throw "payload port mismatch: got=$got want=$Port" }
Write-Host "[release] payload port verified: $got"
if (-not $SkipInstaller) {
  Set-Location (Join-Path $Root "shell")
  Remove-Item Env:ELECTRON_RUN_AS_NODE -ErrorAction SilentlyContinue
  $env:ELECTRON_BUILDER_OFFLINE = "true"
  npx --no-install electron-builder --win nsis --x64
  if ($LASTEXITCODE -ne 0) { throw "installer failed rc=$LASTEXITCODE" }
}
Write-Host "[release] done"
