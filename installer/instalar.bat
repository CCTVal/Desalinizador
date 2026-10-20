@echo off
setlocal

REM ============================================================
REM  Instala, actualiza o desinstala DesalinizadorGotas para el
REM  usuario actual (no requiere permisos de administrador ni Python).
REM ============================================================

set "APP=DesalinizadorGotas"
set "SRC=%~dp0%APP%.exe"
set "DEST=%LOCALAPPDATA%\Programs\%APP%"

set "PKG_VER=desconocida"
if exist "%~dp0version.txt" set /p PKG_VER=<"%~dp0version.txt"

if not exist "%SRC%" (
  echo ERROR: no se encontro %APP%.exe junto a este instalador.
  echo Descomprima el zip completo antes de ejecutar instalar.bat.
  goto fail
)

if not exist "%DEST%\%APP%.exe" goto install_new

set "INST_VER=desconocida"
if exist "%DEST%\version.txt" set /p INST_VER=<"%DEST%\version.txt"
echo El programa ya esta instalado en: %DEST%
echo   Version instalada : %INST_VER%
echo   Version del zip   : %PKG_VER%
if "%INST_VER%"=="%PKG_VER%" echo   (Ya tiene instalada esta misma version.)
echo.
echo   [A] Actualizar a la version de este zip
echo   [D] Desinstalar
echo   [S] Salir sin cambios
choice /c ADS /n /m "Elija una opcion (A/D/S): "
if errorlevel 3 goto end
if errorlevel 2 goto uninstall
goto update

:install_new
echo Instalando version %PKG_VER% en: %DEST%
call :copy_files || goto fail
call :shortcuts
echo.
echo ============================================================
echo  Listo. Abra "Analisis de gotas CCTVal" desde el escritorio
echo  o desde el menu Inicio.
echo ============================================================
goto end

:update
call :close_app || goto end
echo Actualizando a la version %PKG_VER%...
call :copy_files || goto fail
call :shortcuts
echo.
echo ============================================================
echo  Actualizado a la version %PKG_VER%.
echo ============================================================
goto end

:uninstall
call :close_app || goto end
rmdir /s /q "%DEST%"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "foreach ($dir in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))) {" ^
  "  Remove-Item -LiteralPath (Join-Path $dir 'Analisis de gotas CCTVal.lnk') -ErrorAction SilentlyContinue }"
if exist "%DEST%" (
  echo ERROR: no se pudo borrar %DEST%.
  goto fail
)
echo Programa desinstalado.
goto end

REM ------------------------------------------------------------ rutinas
:close_app
REM Si el programa esta abierto, el .exe no se puede reemplazar ni borrar.
tasklist /FI "IMAGENAME eq %APP%.exe" 2>nul | find /I "%APP%.exe" >nul
if errorlevel 1 exit /b 0
echo El programa esta abierto. Guarde su trabajo antes de continuar.
choice /c SN /n /m "Cerrarlo ahora y continuar? (S/N): "
if errorlevel 2 (
  echo Cancelado. No se hicieron cambios.
  exit /b 1
)
taskkill /IM %APP%.exe /F >nul 2>nul
REM Pausa de ~2 s para que Windows libere el .exe (timeout falla sin consola).
ping -n 3 127.0.0.1 >nul
exit /b 0

:copy_files
if not exist "%DEST%" mkdir "%DEST%"
copy /Y "%SRC%" "%DEST%\%APP%.exe" >nul || (
  echo ERROR: no se pudo copiar el programa. Cierrelo si esta abierto
  echo y vuelva a intentarlo.
  exit /b 1
)
if exist "%~dp0version.txt" copy /Y "%~dp0version.txt" "%DEST%\version.txt" >nul
exit /b 0

:shortcuts
echo Creando accesos directos...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$exe = Join-Path $env:LOCALAPPDATA 'Programs\DesalinizadorGotas\DesalinizadorGotas.exe';" ^
  "$shell = New-Object -ComObject WScript.Shell;" ^
  "foreach ($dir in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))) {" ^
  "  $lnk = $shell.CreateShortcut((Join-Path $dir 'Analisis de gotas CCTVal.lnk'));" ^
  "  $lnk.TargetPath = $exe; $lnk.WorkingDirectory = Split-Path $exe; $lnk.IconLocation = $exe; $lnk.Save() }"
if errorlevel 1 (
  echo AVISO: no se pudieron crear los accesos directos.
  echo Puede abrir el programa desde: %DEST%\%APP%.exe
)
exit /b 0

:fail
echo.
pause
exit /b 1

:end
echo.
pause
exit /b 0
