<#
check_win_pa.ps1  --  Win-PA 可用性探针（CW line / CodexWindows · 只读 · 不占 GPU）
形：UTF-8 带 BOM（PS 5.1 读 CJK 需 BOM；本件之「形」为声明项）
端口：读真源 config\system\system_unified.yaml（core.lib.port_config.gateway_port）
      -Port 仅作自测覆盖（⛔ 不用于常规判）
三级判据（⛔ 不合并）：
  L0 端口在听      （面 = 本机 TCP / 端口）
  L1 /health ready （面 = 该端口 /health；须 status=healthy ∧ startup.ready=true）
  L2 真 PA 路由     （面 = 该端口 /v9/pa/roster；须 http 200 ∧ ok=true）
退出码：0 = 可用 ｜ 2 = 不可用（判红）｜ 3 = 入口错（读不到端口真源）
用法： check_win_pa.ps1 [-Quiet] [-WaitSec N] [-Port N]
#>
param(
  [int]$Port = 0,
  [switch]$Quiet,
  [int]$WaitSec = 0
)
$ErrorActionPreference = 'Continue'
Set-Location (Join-Path $PSScriptRoot '..\..')   # ⛔ 硬编开发机之径
$t0 = Get-Date
function Say($s) { if (-not $Quiet) { Write-Output $s } }
function Probe([int]$prt) {
  $r = [ordered]@{ port = $prt; pid = $null; l0 = $false; l1 = $false; l1raw = ''; l2 = $false; l2raw = '' }
  try {
    $c = Get-NetTCPConnection -State Listen -LocalPort $prt -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($c) { $r.l0 = $true; $r.pid = $c.OwningProcess }
  } catch {}
  if (-not $r.l0) { return $r }
  try {
    $h = Invoke-WebRequest ("http://127.0.0.1:{0}/health" -f $prt) -TimeoutSec 8 -UseBasicParsing
    $j = $h.Content | ConvertFrom-Json
    $r.l1raw = ("http={0} status={1} ready={2} progress={3} version={4}" -f $h.StatusCode, $j.status, $j.startup.ready, $j.startup.progress, $j.version)
    if ($h.StatusCode -eq 200 -and $j.status -eq 'healthy' -and $j.startup.ready -eq $true) { $r.l1 = $true }
  } catch { $r.l1raw = "ERR " + $_.Exception.Message }
  if (-not $r.l1) { return $r }
  try {
    $g = Invoke-WebRequest ("http://127.0.0.1:{0}/v9/pa/roster" -f $prt) -TimeoutSec 8 -UseBasicParsing
    $k = $g.Content | ConvertFrom-Json
    $r.l2raw = ("http={0} ok={1} count={2}" -f $g.StatusCode, $k.ok, $k.count)
    if ($g.StatusCode -eq 200 -and $k.ok -eq $true) { $r.l2 = $true }
  } catch { $r.l2raw = "ERR " + $_.Exception.Message }
  return $r
}
$srcNote = '真源 config/system/system_unified.yaml'
$prt = $Port
if ($prt -le 0) {
  $line = $null
  try {
    $out = & python -c "import sys;sys.path.insert(0,'.');from core.lib.port_config import gateway_port;print(gateway_port())" 2>$null
    $line = ($out | Where-Object { $_ -match '^\s*\d+\s*$' } | Select-Object -Last 1)
  } catch {}
  if ($line) { $prt = [int]$line.Trim() }
} else { $srcNote = '参数覆盖 -Port（仅供自测）' }
if ($prt -le 0) {
  Say ("[PA] 报刻 {0} ｜ 入口错：读不到端口真源（{1}）" -f $t0.ToString('yyyy-MM-dd HH:mm:ss'), $srcNote)
  exit 3
}
$deadline = $t0.AddSeconds($WaitSec)
$r = Probe $prt
while (-not $r.l2 -and (Get-Date) -lt $deadline) { Start-Sleep -Seconds 10; $r = Probe $prt }
$te = Get-Date
$verdict = if ($r.l2) { '可用' } elseif ($r.l0) { '半可用' } else { '不可用' }
Say ("[PA] 报刻 {0} ｜ 取数刻 {1} ｜ 端口 {2}（{3}）｜ PID {4}" -f $t0.ToString('yyyy-MM-dd HH:mm:ss'), $te.ToString('yyyy-MM-dd HH:mm:ss'), $prt, $srcNote, [string]$r.pid)
Say ("[PA] L0 端口在听 = {0}" -f $r.l0)
Say ("[PA] L1 /health    = {0} ｜ {1}" -f $r.l1, $r.l1raw)
Say ("[PA] L2 PA 路由    = {0} ｜ {1}" -f $r.l2, $r.l2raw)
Say ("[PA] 判：{0}" -f $verdict)
if ($r.l2) { exit 0 } else { exit 2 }