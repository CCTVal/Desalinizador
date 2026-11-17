$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path '.venv/Scripts/python.exe')) {
    throw 'Falta el entorno Python. Sigue la instalación del README.md.'
}
if (-not (Test-Path 'dist/index.html')) {
    throw 'Falta construir el visor. Ejecuta npm.cmd run build.'
}
& './.venv/Scripts/python.exe' -m uvicorn src.server:app --host 127.0.0.1 --port 8001
