@echo off
setlocal

REM ============================================================
REM  Genera el ejecutable .exe de la aplicacion del desalinizador
REM ============================================================
REM  Requisitos:
REM    %PYTHON_CMD% -m pip install -r requirements.txt
REM
REM  Si hay varios Python instalados, puede forzar uno asi:
REM    set "PYTHON_CMD=py -3.12"
REM    build.bat
REM
REM  El .exe quedara en: dist\DesalinizadorGotas.exe
REM ============================================================

if not "%PYTHON_CMD%"=="" goto check_python

set "PYTHON_CMD=python"
call :check_candidate >nul 2>nul
if not errorlevel 1 goto check_python

set "PYTHON_CMD=py -3.12"
call :check_candidate >nul 2>nul
if not errorlevel 1 goto check_python

set "PYTHON_CMD=py -3.11"
call :check_candidate >nul 2>nul
if not errorlevel 1 goto check_python

echo ERROR: no se encontro un Python usable con tkinter y dependencias.
echo Pruebe instalando Python desde python.org con la opcion Tcl/Tk activada.
exit /b 1

:check_python
echo Usando Python: %PYTHON_CMD%
call :check_candidate
if errorlevel 1 (
  echo.
  echo ERROR: el Python seleccionado no puede importar tkinter, cv2, numpy, matplotlib y PIL.
  echo Instale dependencias con:
  echo   %PYTHON_CMD% -m pip install -r requirements.txt
  echo Si tkinter falla, reinstale Python con Tcl/Tk o use otro Python:
  echo   set "PYTHON_CMD=py -3.12"
  exit /b 1
)

%PYTHON_CMD% -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
  echo.
  echo ERROR: PyInstaller no esta instalado en este Python.
  echo Instale dependencias con:
  echo   %PYTHON_CMD% -m pip install -r requirements.txt
  exit /b 1
)

echo.
echo Generando ejecutable...
%PYTHON_CMD% -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name "DesalinizadorGotas" ^
  --hidden-import "matplotlib.backends.backend_tkagg" ^
  --collect-data matplotlib ^
  --exclude-module PyQt5 ^
  --exclude-module PyQt6 ^
  --exclude-module PySide2 ^
  --exclude-module PySide6 ^
  --exclude-module IPython ^
  --exclude-module notebook ^
  --exclude-module sphinx ^
  --exclude-module vtk ^
  --exclude-module vtkmodules ^
  app.py

if errorlevel 1 (
  echo.
  echo ERROR: PyInstaller fallo. Revise el log anterior.
  exit /b 1
)

if not exist "dist\DesalinizadorGotas.exe" (
  echo.
  echo ERROR: PyInstaller termino, pero no se encontro dist\DesalinizadorGotas.exe.
  exit /b 1
)

echo.
echo ============================================================
echo  Listo. El ejecutable esta en: dist\DesalinizadorGotas.exe
echo ============================================================
exit /b 0

:check_candidate
%PYTHON_CMD% -c "import tkinter as tk; root=tk.Tk(); root.destroy(); import cv2, numpy, matplotlib, PIL" >nul 2>nul
exit /b %errorlevel%
