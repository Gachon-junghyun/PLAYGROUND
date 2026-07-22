# Hindsight 서버 실행 (PowerShell).
# 사용: 먼저 토큰을 설정한 뒤 이 스크립트를 PLAY 디렉토리에서 실행.
#   $env:HINDSIGHT_TOKEN = "여기에-긴-무작위-토큰"
#   .\run.ps1

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

if (-not $env:HINDSIGHT_TOKEN) {
    Write-Host "HINDSIGHT_TOKEN 이 설정되지 않았습니다. 먼저:" -ForegroundColor Yellow
    Write-Host '  $env:HINDSIGHT_TOKEN = "긴-무작위-토큰"' -ForegroundColor Yellow
    exit 1
}

$bind = if ($env:HINDSIGHT_HOST) { $env:HINDSIGHT_HOST } else { "0.0.0.0" }
$port = if ($env:HINDSIGHT_PORT) { $env:HINDSIGHT_PORT } else { "8000" }

python -m uvicorn server:app --host $bind --port $port
