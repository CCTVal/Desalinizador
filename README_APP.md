# Aplicación de escritorio - Detector de Gotas

Interfaz gráfica nativa de Windows para `gotas.py`. Permite subir una imagen
de la cámara de humidificación del desalinizador, analizarla, ver las imágenes
anotadas y los gráficos de distribución de anchos, todo dentro de la aplicación.

## Archivos

- `app.py` — interfaz gráfica (Tkinter).
- `detector.py` — lógica de detección de gotas (refactorizada desde `gotas.py`).
- `gotas.py` — script original de línea de comandos (sin cambios).
- `requirements.txt` — dependencias de Python.
- `build.bat` — script para generar el ejecutable `.exe`.

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

## Uso de la aplicación

1. **Abrir imagen…** — seleccionar la foto a analizar.
2. **Lente** — elegir el lente con el que se tomó la foto (Tamron o Sigma),
   ya que define los umbrales de oscuridad.
3. **Analizar** — ejecuta la detección.
4. Pestaña **Imágenes** — ver la detección (cajas verdes), la original o el
   debug (núcleos pintados de rojo).
5. Pestaña **Gráficos** — histograma de anchos con la media y ±1σ.
6. La barra inferior muestra el conteo de gotas y las estadísticas.
