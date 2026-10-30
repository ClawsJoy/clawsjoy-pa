# dsh_home_migrate.ps1
# DSH home C: -> D: migration. Default = DryRun.
# -Go only after you QUIT DSH (no DeepSeek Harness.exe).
# Junction-aware: /XJ /SL + recreate 482 node_modules junctions.
param(
  [string]$Source = "C:\Users\flybo\.dsh",
  [string]$Target = "D:\dsh-home",
  [switch]$Go,
  [switch]$NoJunction
)
$ErrorActionPreference = "Stop"
function Say($m) { Write-Host $m }
function Fail($m) { Write-Host "[FAIL] $m" -ForegroundColor Red; exit 2 }

if (-not (Test-Path $Source)) { Fail "source missing: $Source" }
$srcFiles = Get-ChildItem $Source -Recurse -File -ErrorAction SilentlyContinue
$srcCount = ($srcFiles | Measure-Object).Count
$srcBytes = ($srcFiles | Measure-Object Length -Sum).Sum
$v3 = (Get-ChildItem "$Source\sessions" -Recurse -Filter "session.v3.jsonl.zstd" -ErrorAction SilentlyContinue | Measure-Object).Count
$junctions = @()
try {
  $junctions = Get-ChildItem $Source -Recurse -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Attributes -match "ReparsePoint" } |
    ForEach-Object {
      [pscustomobject]@{
        Rel = $_.FullName.Substring($Source.Length).TrimStart("\")
        Target = @($_.Target)[0]
      }
    }
} catch {}
Say "SOURCE $Source files=$srcCount bytes=$srcBytes v3=$v3 junctions=$($junctions.Count)"
Say "TARGET $Target exists=$(Test-Path $Target)"
$d = Get-PSDrive D
Say ("D free GB=" + [math]::Round($d.Free/1GB,1))
if ($d.Free -lt ($srcBytes * 1.2)) { Fail "D free < 1.2x source" }

$hits = @()
try {
  $hits = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessId -ne $PID -and
    ($_.Name -match "DeepSeek Harness|^(dsh|node)$") -and
    $_.CommandLine -and
    ($_.CommandLine -match "DeepSeek Harness|app\.asar|\.dsh")
  }
} catch {}
Say ("processes using source=" + $hits.Count)
$hits | ForEach-Object { Say ("  pid=" + $_.ProcessId + " " + $_.Name) }

if (-not $Go) {
  Say ""
  Say "DRY RUN. Plan:"
  Say "  1) quit DSH (DeepSeek Harness.exe); verify processes using source = 0"
  Say "  2) robocopy SOURCE TARGET /MIR /COPY:DAT /DCOPY:DAT /XJ /SL"
  Say "  3) verify files=$srcCount bytes=$srcBytes v3=$v3"
  Say "  4) recreate $($junctions.Count) junctions"
  Say "  5) rename source -> $Source.backup_<timestamp>"
  Say "  6) set User DSH_HOME=$Target"
  Say "  7) junction $Source -> $Target (unless -NoJunction)"
  Say "  8) start: dsh --profile web"
  Say "Run with -Go ONLY after DSH is stopped."
  exit 0
}

if ($hits.Count -gt 0) { Fail "DSH still running; quit all DeepSeek Harness.exe first" }
if (Test-Path $Target) {
  $tf = Get-ChildItem $Target -Recurse -File -ErrorAction SilentlyContinue
  if (($tf | Measure-Object).Count -gt 0) { Fail "target non-empty; remove after backup" }
  Remove-Item $Target -Recurse -Force
  Say "removed empty target"
}

$log = Join-Path $env:TEMP ("dsh_migrate_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".log")
robocopy $Source $Target /MIR /COPY:DAT /DCOPY:DAT /XJ /SL /R:2 /W:2 /LOG:$log
$rc = $LASTEXITCODE
Say "robocopy rc=$rc log=$log"
if ($rc -ge 8) { Fail "robocopy failed rc=$rc" }

$dstFiles = Get-ChildItem $Target -Recurse -File -ErrorAction SilentlyContinue
$dstCount = ($dstFiles | Measure-Object).Count
$dstBytes = ($dstFiles | Measure-Object Length -Sum).Sum
Say "TARGET files=$dstCount bytes=$dstBytes"
if ($dstCount -ne $srcCount -or $dstBytes -ne $srcBytes) { Fail "verification mismatch (files/bytes)" }

$made = 0
foreach ($j in $junctions) {
  $tp = Join-Path $Target $j.Rel
  if (Test-Path $tp) { continue }
  $par = Split-Path $tp -Parent
  New-Item -ItemType Directory -Force -Path $par | Out-Null
  New-Item -ItemType Junction -Path $tp -Target $j.Target | Out-Null
  $made++
}
$dstJ = @(Get-ChildItem $Target -Recurse -Force -ErrorAction SilentlyContinue | Where-Object { $_.Attributes -match "ReparsePoint" })
Say "TARGET junctions=$($dstJ.Count) made=$made expected=$($junctions.Count)"
if ($dstJ.Count -ne $junctions.Count) { Fail "junction count mismatch" }

$bak = "$Source.backup_" + (Get-Date -Format "yyyyMMdd_HHmmss")
Rename-Item -Path $Source -NewName (Split-Path $bak -Leaf)
Say "source renamed -> $bak"
if (-not $NoJunction) {
  New-Item -ItemType Junction -Path $Source -Target $Target | Out-Null
  Say "junction $Source -> $Target"
}
[Environment]::SetEnvironmentVariable("DSH_HOME", $Target, "User")
Say "User DSH_HOME=$Target"
Say "DONE. Rollback: remove junction, rename backup back, clear User DSH_HOME."
Say "Start: dsh --profile web"
