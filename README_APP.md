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

- `Instalar_DesalinizadorGotas.exe` — instalador gráfico autocontenido, con el
  logo y los colores de CCTVal. Incluye la aplicación completa.
- `instalar.bat` — una alternativa para abrir el mismo instalador gráfico.
- `version.txt` — fecha del `.exe` y commit, para detectar actualizaciones.
- `LEEME.txt` — instrucciones para el usuario final.

En el otro PC: descomprimir el zip y abrir `Instalar_DesalinizadorGotas.exe`.
No necesita Python, conexión a Internet ni permisos de administrador. La ventana
ofrece **Instalar programa** cuando no existe una instalación y **Actualizar
programa** cuando ya está instalado. Muestra las versiones, la carpeta de destino
y el progreso, y permite abrir o desinstalar el programa. **Elegir carpeta** permite
cambiar el destino o seleccionar una instalación existente para actualizarla.
La ubicación se recuerda tras instalar o actualizar. Cerrar la aplicación
antes de actualizar o desinstalar. Una actualización fallida conserva el
ejecutable anterior; la desinstalación conserva los archivos personales.

### Problemas conocidos al compilar

- `build.bat` utiliza `build\entorno_instalador\Scripts\python.exe` si existe
  y tiene las dependencias. También puede elegirse otro Python con `PYTHON_CMD`.
- La compilación incluye las carpetas y DLL de Tcl/Tk del mismo Python.
  Esto evita depender de Tcl/Tk
  instalado en el equipo de destino.
- `python qa_installer_gui.py` prueba los botones, instalación, actualización,
  accesos directos y desinstalación en carpetas aisladas dentro de `build`.
  `python packaging/verify_installer.py` comprueba el ZIP, el programa incluido
  y el arranque del instalador compilado.
  Ejecutar esta comprobación en una sesión normal de Windows: un entorno
  restringido puede impedir que Tcl lea la carpeta temporal del ejecutable y
  producir un fallo de arranque que no ocurre fuera de ese entorno.

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
   Justo debajo aparece el **Diámetro de Sauter global**, calculado como
   Σd³ / Σd² de todas las gotas de las fotos analizadas (no como promedio
   de los diámetros de Sauter por foto). Se muestra en µm si hay calibración,
   o en px si no la hay; sin gotas se informa 0.
6. **Exportar Excel** guarda las medidas, el resumen de todo el lote y los
   valores de Oscuridad y Enfoque usados en el último análisis confirmado.
   En el resumen global, **Diámetro de Sauter (µm)** aparece inmediatamente
   después de **Desviación global (µm)** (ambos en px sin calibración).
   La exportación de una sola foto también incluye su diámetro de Sauter.
