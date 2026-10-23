param([int]$Port = 8766)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$sitePython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $sitePython)) { $sitePython = 'python' }
& $sitePython -m uvicorn portal.app:app --host 127.0.0.1 --port $Port
