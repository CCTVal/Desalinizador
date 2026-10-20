# Aplicación de escritorio - Detector de Gotas

Interfaz gráfica nativa de Windows para el análisis de gotas. Permite subir
varias imágenes de la cámara de humidificación del desalinizador, analizarlas y
revisar sus imágenes anotadas, gráficos y estadísticas dentro de la aplicación.

## Archivos

- `app.py` — interfaz gráfica (Tkinter).
- `detector.py` — lógica de detección de gotas (refactorizada desde `gotas.py`).
- `excel_export.py` — exportación a Excel (foto o lote) y totales del lote.
- `gotas.py` — script original de línea de comandos (sin cambios).
- `requirements.txt` — dependencias de Python.
- `build.bat` — script para generar el ejecutable `.exe`.
- `build_zip.ps1` — genera el `.exe` y lo empaqueta en un instalador `.zip`.
- `installer/` — archivos que van dentro del zip (`instalar.bat`, `LEEME.txt`).
- `qa_all.py` — corre todas las pruebas (`qa_test`, `qa_front`, `qa_batch`,
  `qa_calcular` e integración).

## Ejecutar en modo desarrollo

```bash
pip install -r requirements.txt
python app.py
```

## Generar el ejecutable (.exe)

1. Instalar dependencias (incluye PyInstaller):

   ```bash
   pip install -r requirements.txt
   ```

2. Ejecutar el script de build (doble clic o desde la terminal):

   ```bash
   build.bat
   ```

3. El ejecutable quedará en:

   ```
   dist\DesalinizadorGotas.exe
   ```

   Ese `.exe` es autocontenido: se puede copiar y ejecutar en otro Windows
   sin necesidad de tener Python instalado.

## Generar el instalador (.zip)

Desde PowerShell, en la carpeta del proyecto:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_zip.ps1
```

Genera el `.exe` y crea `dist\DesalinizadorGotas_instalador.zip` con:

- `DesalinizadorGotas.exe` — la aplicación (se puede usar sin instalar).
- `instalar.bat` — la copia a `%LOCALAPPDATA%\Programs\DesalinizadorGotas` y
  crea accesos directos en el escritorio y en el menú Inicio.
- `LEEME.txt` — instrucciones para el usuario final.

En el otro PC: descomprimir el zip y ejecutar `instalar.bat`. No necesita
Python ni permisos de administrador.

### Problemas conocidos al compilar

- **Python 3.10.0** hace fallar a PyInstaller (`IndexError: tuple index out of
  range` en `dis.py`). Use otro Python, por ejemplo `set "PYTHON_CMD=py -3.12"`.
- **Python de Anaconda**: compilar directamente con él da un `.exe` de ~290 MB.
  Con un entorno virtual y paquetes de pip queda en ~80 MB, pero hay que poner
  `<anaconda>\Library\bin` en el `PATH` al compilar; si no, el `.exe` falla al
  abrir (`DLL load failed while importing _ctypes` / `_tkinter`).

## Uso de la aplicación

1. Cargar la foto de la regla y confirmar la calibración, o continuar sin ella.
2. En **Gotas**, elegir una o varias fotos (o arrastrarlas si está disponible).
   Se pueden añadir más y quitar las seleccionadas antes de analizar.
3. Pulsar **Analizar** para procesar todas las fotos con la misma calibración.
4. En **Resultados**, usar **Anterior** y **Siguiente** para revisar cada foto:
   imagen anotada, histograma y estadísticas. El zoom y el arrastre afectan
   solo la visualización de la foto actual.
5. Los controles **Oscuridad** y **Enfoque** solo cambian los valores; el botón
   **Calcular** (junto al zoom) recalcula todas las fotos con ellos. Con varias
   fotos, la línea **Lote** muestra los totales del lote.
6. **Exportar Excel** guarda las medidas, el resumen de todo el lote y los
   valores de Oscuridad y Enfoque usados.
