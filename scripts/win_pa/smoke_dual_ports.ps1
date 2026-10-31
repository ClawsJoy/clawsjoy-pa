# Regression smoke: installed 5103 and dev 5102 must both answer, with distinct builds.
param(
  [int]$InstalledPort = 5103,
  [int]$DevPort = 5102
)
function Get-Health([int]$Port) {
  try { return Invoke-RestMethod -UseBasicParsing ("http://127.0.0.1:{0}/health" -f $Port) -TimeoutSec 5 }
  catch { return $null }
}
$inst = Get-Health $InstalledPort
$dev = Get-Health $DevPort
if (-not $inst) { Write-Host "[smoke] FAIL installed :$InstalledPort has no health"; exit 2 }
if (-not $dev) { Write-Host "[smoke] FAIL dev :$DevPort has no health"; exit 2 }
if ($inst.build.path -eq $dev.build.path) { Write-Host "[smoke] FAIL same build.path => not isolated"; exit 2 }
Write-Host ("[smoke] installed :" + $InstalledPort + " version=" + $inst.version + " build=" + $inst.build.path)
Write-Host ("[smoke] dev       :" + $DevPort + " version=" + $dev.version + " build=" + $dev.build.path)
Write-Host "[smoke] PASS"
exit 0
