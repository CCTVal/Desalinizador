# Genera dist\DesalinizadorGotas.exe (con build.bat) y lo empaqueta junto al
# instalador en dist\DesalinizadorGotas_instalador.zip.
#
# Uso:  powershell -ExecutionPolicy Bypass -File .\build_zip.ps1
#       (-SkipBuild reutiliza el .exe ya generado)
param([switch]$SkipBuild, [string]$Python = "")

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$exe = Join-Path $PSScriptRoot "dist\DesalinizadorGotas.exe"
$zip = Join-Path $PSScriptRoot "dist\DesalinizadorGotas_instalador.zip"
$stage = Join-Path $PSScriptRoot "dist\zip_stage"
$gui = Join-Path $PSScriptRoot "dist\Instalar_DesalinizadorGotas.exe"
$payload = Join-Path $PSScriptRoot "build\installer_payload"

if (-not $SkipBuild) {
    & (Join-Path $PSScriptRoot "build.bat")
    if ($LASTEXITCODE -ne 0) { throw "build.bat fallo (codigo $LASTEXITCODE)." }
}
if (-not (Test-Path -LiteralPath $exe)) { throw "No existe $exe." }

New-Item -ItemType Directory -Path $payload -Force | Out-Null
$version = (Get-Item -LiteralPath $exe).LastWriteTime.ToString("yyyy-MM-dd HH:mm")
$commit = git rev-parse --short HEAD 2>$null
if ($LASTEXITCODE -eq 0 -and $commit) { $version += " ($commit)" }
Set-Content -LiteralPath (Join-Path $payload "version.txt") -Value $version -Encoding UTF8
if (-not $Python) {
    $Python = Join-Path $PSScriptRoot "build\entorno_instalador\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $Python)) { $Python = "python" }
}
& $Python (Join-Path $PSScriptRoot "packaging\build_app.py") --installer
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $gui)) {
    throw "No se pudo compilar el instalador grafico."
}
$stage = [IO.Path]::GetFullPath($stage)
$distRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "dist")).TrimEnd('\') + '\'
if (-not $stage.StartsWith($distRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Carpeta temporal fuera de dist."
}

if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
New-Item -ItemType Directory -Path $stage | Out-Null
Copy-Item -LiteralPath $gui -Destination $stage
Copy-Item -Path (Join-Path $PSScriptRoot "installer\*") -Destination $stage

# Versión que instalar.bat compara con la instalada: fecha del .exe + commit.
Copy-Item -LiteralPath (Join-Path $payload "version.txt") -Destination $stage

if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force }
Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zip
Remove-Item -LiteralPath $stage -Recurse -Force

$mb = [math]::Round((Get-Item -LiteralPath $zip).Length / 1MB, 1)
Write-Host "Listo: $zip ($mb MB)"
