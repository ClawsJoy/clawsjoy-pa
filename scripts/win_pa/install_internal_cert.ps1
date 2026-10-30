# ClawsJoy PA 内部自签证书导入（仅可信用户）
# 只导入公钥 .cer；不接触 PFX 私钥。
[CmdletBinding()]
param(
  [string]$CerPath = (Join-Path $PSScriptRoot 'ClawsJoy_Internal.cer'),
  [string]$Thumbprint = '654F9E0CE9709A5FCB5A8B3347C1E7293F930651',
  [ValidateSet('CurrentUser','LocalMachine')][string]$Scope = 'CurrentUser'
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $CerPath)) { throw "找不到证书：$CerPath" }
$cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($CerPath)
if ($cert.Thumbprint -ne $Thumbprint) { throw "证书指纹不符：期望 $Thumbprint，实得 $($cert.Thumbprint)" }
if ($Scope -eq 'LocalMachine') {
  $admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
  if (-not $admin) { throw 'LocalMachine 需要以管理员身份运行；或改用 -Scope CurrentUser' }
  $root = 'Cert:\LocalMachine\Root'; $pub = 'Cert:\LocalMachine\TrustedPublisher'
} else {
  $root = 'Cert:\CurrentUser\Root'; $pub = 'Cert:\CurrentUser\TrustedPublisher'
}
Import-Certificate -FilePath $CerPath -CertStoreLocation $root | Out-Null
Import-Certificate -FilePath $CerPath -CertStoreLocation $pub | Out-Null
Write-Host "已导入：$($cert.Subject)  Thumbprint=$($cert.Thumbprint)  Scope=$Scope" -ForegroundColor Green
Write-Host '提醒：这只让本机信任该发布者；不解决 SmartScreen。' -ForegroundColor Yellow
