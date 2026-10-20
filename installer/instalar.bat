@echo off
setlocal

REM ============================================================
REM  Instala DesalinizadorGotas para el usuario actual
REM  (no requiere permisos de administrador ni Python).
REM ============================================================

set "SRC=%~dp0DesalinizadorGotas.exe"
set "DEST=%LOCALAPPDATA%\Programs\DesalinizadorGotas"

if not exist "%SRC%" (
  echo ERROR: no se encontro DesalinizadorGotas.exe junto a este instalador.
  echo Descomprima el zip completo antes de ejecutar instalar.bat.
  pause
  exit /b 1
)

echo Instalando en: %DEST%
if not exist "%DEST%" mkdir "%DEST%"
copy /Y "%SRC%" "%DEST%\DesalinizadorGotas.exe" >nul
if errorlevel 1 (
  echo ERROR: no se pudo copiar el programa. Cierre la aplicacion si esta abierta
  echo y vuelva a intentarlo.
  pause
  exit /b 1
)

echo Creando accesos directos...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$exe = Join-Path $env:LOCALAPPDATA 'Programs\DesalinizadorGotas\DesalinizadorGotas.exe';" ^
  "$shell = New-Object -ComObject WScript.Shell;" ^
  "foreach ($dir in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))) {" ^
  "  $lnk = $shell.CreateShortcut((Join-Path $dir 'Analisis de gotas CCTVal.lnk'));" ^
  "  $lnk.TargetPath = $exe; $lnk.WorkingDirectory = Split-Path $exe; $lnk.IconLocation = $exe; $lnk.Save() }"
if errorlevel 1 (
  echo AVISO: no se pudieron crear los accesos directos.
  echo Puede abrir el programa desde: %DEST%\DesalinizadorGotas.exe
)

echo.
echo ============================================================
echo  Listo. Abra "Analisis de gotas CCTVal" desde el escritorio
echo  o desde el menu Inicio.
echo ============================================================
pause
exit /b 0
