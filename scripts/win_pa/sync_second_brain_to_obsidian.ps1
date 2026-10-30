# 同步第一大脑开发计划到 Obsidian pa/ (copy, not move)
param(
  [string]$Vault = 'D:\Obsidian\ClawsJoy\ClawsJoy',
  [string]$Sub = 'pa\开发计划_20261029'
)
$ErrorActionPreference='Stop'
$src = Join-Path (Get-Location) 'docs\second_brain'
$dst = Join-Path $Vault $Sub
if (-not (Test-Path $src)) { throw "源不存在：$src" }
New-Item -ItemType Directory -Force -Path $dst | Out-Null
Get-ChildItem $src -Filter *.md -File | Copy-Item -Destination $dst -Force
Write-Host "已同步 $((Get-ChildItem $src -Filter *.md -File).Count) 件 -> $dst" -ForegroundColor Green
Write-Host '提示：源仍是 docs/second_brain；本目录是副本。' -ForegroundColor Yellow
