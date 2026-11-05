param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$raiz = $PSScriptRoot
$dist = Join-Path $raiz "dist"
$comentario = Join-Path $raiz "packaging\pnp_instalador_sfx.txt"
$portable = Join-Path $dist "ConversorPnP.exe"
$instalador = Join-Path $dist "ConversorPnP_Instalador.exe"
$archivoRar = Join-Path $dist "ConversorPnP_Instalador.rar"
$rar = Join-Path $env:ProgramFiles "WinRAR\Rar.exe"
if (-not (Test-Path -LiteralPath $rar)) {
    $rar = Join-Path ${env:ProgramFiles(x86)} "WinRAR\Rar.exe"
}
if (-not (Test-Path -LiteralPath $rar)) {
    throw "No se encontro WinRAR (Rar.exe) en este equipo."
}

Push-Location -LiteralPath $raiz
try {
    & $Python -c "from PyQt6.QtWidgets import QApplication; import PyInstaller"
    if ($LASTEXITCODE -ne 0) {
        throw "Instala PyQt6 y PyInstaller en el Python seleccionado."
    }

    & $Python -m PyInstaller --noconfirm --clean --onefile --windowed `
        --name ConversorPnP `
        --icon (Join-Path $raiz "assets\cctval_icon.ico") `
        --add-data "$(Join-Path $raiz 'assets\cctval_icon.png');assets" `
        --exclude-module PyQt5 --exclude-module PySide2 --exclude-module PySide6 `
        --exclude-module tkinter `
        --specpath (Join-Path $raiz "build\pnp_spec") `
        --workpath (Join-Path $raiz "build\pnp_work") `
        --distpath $dist `
        (Join-Path $raiz "convertir_pnp.py")
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $portable)) {
        throw "No se pudo generar el ejecutable portatil."
    }

    foreach ($archivo in @($instalador, $archivoRar)) {
        $rutaAbsoluta = [System.IO.Path]::GetFullPath($archivo)
        $carpetaDist = [System.IO.Path]::GetFullPath($dist).TrimEnd('\') + '\'
        if (-not $rutaAbsoluta.StartsWith($carpetaDist, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Ruta de salida fuera de dist: $rutaAbsoluta"
        }
        if (Test-Path -LiteralPath $rutaAbsoluta) {
            Remove-Item -LiteralPath $rutaAbsoluta -Force
        }
    }

    & $rar a -ep -ma5 -m5 -sfx "-z$comentario" $instalador $portable
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $instalador)) {
        throw "No se pudo generar el instalador autoextraible."
    }
    & $rar t $instalador
    if ($LASTEXITCODE -ne 0) {
        throw "El instalador no supero la comprobacion de WinRAR."
    }

    & $rar a -ep -ma5 -m0 $archivoRar $instalador (Join-Path $raiz "README_INSTALADOR_PNP.md")
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $archivoRar)) {
        throw "No se pudo generar el archivo RAR."
    }
    & $rar t $archivoRar
    if ($LASTEXITCODE -ne 0) {
        throw "El archivo RAR no supero la comprobacion de WinRAR."
    }

    Write-Host "Instalador: $instalador"
    Write-Host "Archivo RAR: $archivoRar"
    Write-Host "Ejecutable portatil: $portable"
}
finally {
    Pop-Location
}
