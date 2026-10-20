# Genera dist\DesalinizadorGotas.exe (con build.bat) y lo empaqueta junto al
# instalador en dist\DesalinizadorGotas_instalador.zip.
#
# Uso:  powershell -ExecutionPolicy Bypass -File .\build_zip.ps1
#       (-SkipBuild reutiliza el .exe ya generado)
param([switch]$SkipBuild)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$exe = Join-Path $PSScriptRoot "dist\DesalinizadorGotas.exe"
$zip = Join-Path $PSScriptRoot "dist\DesalinizadorGotas_instalador.zip"
$stage = Join-Path $PSScriptRoot "dist\zip_stage"

if (-not $SkipBuild) {
    & (Join-Path $PSScriptRoot "build.bat")
    if ($LASTEXITCODE -ne 0) { throw "build.bat fallo (codigo $LASTEXITCODE)." }
}
if (-not (Test-Path -LiteralPath $exe)) { throw "No existe $exe." }

if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
New-Item -ItemType Directory -Path $stage | Out-Null
Copy-Item -LiteralPath $exe -Destination $stage
Copy-Item -Path (Join-Path $PSScriptRoot "installer\*") -Destination $stage

if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force }
Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zip
Remove-Item -LiteralPath $stage -Recurse -Force

$mb = [math]::Round((Get-Item -LiteralPath $zip).Length / 1MB, 1)
Write-Host "Listo: $zip ($mb MB)"
