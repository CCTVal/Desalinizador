@echo off
REM ============================================================
REM  Genera el ejecutable .exe de la aplicacion del desalinizador
REM ============================================================
REM  Requisitos: tener instaladas las dependencias (requirements.txt)
REM     pip install -r requirements.txt
REM
REM  El .exe quedara en la carpeta: dist\DesalinizadorGotas.exe
REM ============================================================

echo Generando ejecutable...

pyinstaller --noconfirm --onefile --windowed ^
  --name "DesalinizadorGotas" ^
  --collect-all matplotlib ^
  --collect-all cv2 ^
  app.py

echo.
echo ============================================================
echo  Listo. El ejecutable esta en: dist\DesalinizadorGotas.exe
echo ============================================================
pause
