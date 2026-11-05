@echo off
setlocal
if not exist "%~dp0Instalar_DesalinizadorGotas.exe" (
  echo No se encontro el instalador grafico. Descomprima el paquete completo.
  pause
  exit /b 1
)
start "" "%~dp0Instalar_DesalinizadorGotas.exe"
exit /b 0
