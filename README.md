# Desalinizador

Este proyecto lee una imagen de la cámara de humidificación del desalinizador y
entrega los **anchos de las gotas** que están en suspensión, junto con
estadísticas (cantidad, tamaño promedio y desviación estándar).

Incluye dos formas de uso:

1. **Script de línea de comandos** (`gotas.py`) — el código original.
2. **Aplicación de escritorio** (`app.py`) — interfaz gráfica con calibración,
   detección, gráficos y zoom, empaquetable como ejecutable `.exe` de Windows.

Cualquier duda, por favor dirigirla a Sebastián Vidal, coordinador de este
desarrollo.

---

## Índice

- [1. Script de línea de comandos](#1-script-de-línea-de-comandos)
- [2. Aplicación de escritorio (front-end)](#2-aplicación-de-escritorio-front-end)
  - [2.1 Archivos](#21-archivos)
  - [2.2 Ejecutar en modo desarrollo](#22-ejecutar-en-modo-desarrollo)
  - [2.3 Generar el ejecutable (.exe)](#23-generar-el-ejecutable-exe)
  - [2.4 Uso de la aplicación](#24-uso-de-la-aplicación)
- [3. Backend — Cálculos y variables](#3-backend--cálculos-y-variables)
  - [3.1 Calibración cm/mm → µm por píxel](#31-calibración-cmmm--µm-por-píxel)
  - [3.2 Detección y medición de gotas](#32-detección-y-medición-de-gotas)

---

## 1. Script de línea de comandos

Para correr el código original, ejecutar `python gotas.py <ruta_imagen>` donde
el argumento es el nombre del archivo con la foto a analizar. Por ejemplo:

```bash
python gotas.py DSC_0111.JPG
```

Genera imágenes anotadas (`*_new.jpg`, `*_debug.jpg`) e imprime las
estadísticas en consola.

---

## 2. Aplicación de escritorio (front-end)

Interfaz gráfica nativa de Windows para el análisis de gotas. Permite subir una
foto, calibrar la escala con una regla, ver las imágenes anotadas y los
gráficos de distribución de tamaños, todo dentro de la aplicación, con zoom.

### 2.1 Archivos

- `app.py` — interfaz gráfica (Tkinter), con dos pestañas.
- `detector.py` — lógica de detección y calibración (refactorizada desde `gotas.py`).
- `gotas.py` — script original de línea de comandos (sin cambios).
- `requirements.txt` — dependencias de Python.
- `build.bat` — script para generar el ejecutable `.exe`.

### 2.2 Ejecutar en modo desarrollo

```bash
pip install -r requirements.txt
python app.py
```

### 2.3 Generar el ejecutable (.exe)

1. Instalar dependencias (incluye PyInstaller):

   ```bash
   pip install -r requirements.txt
   ```

2. Ejecutar el script de build (doble clic o desde la terminal):

   ```bash
   build.bat
   ```

3. El ejecutable quedará en `dist\DesalinizadorGotas.exe`. Es autocontenido: se
   puede copiar y ejecutar en otro Windows sin tener Python instalado.

> Nota: para reconstruir el `.exe` la aplicación debe estar **cerrada** (si está
> abierta, bloquea el archivo).

### 2.4 Uso de la aplicación

**Pestaña 1 · Calibración (referencia)**

1. **Subir archivo referencia** — cargar la foto de la regla.
2. La separación entre marcas se **detecta automáticamente** (se dibujan en azul
   sobre la imagen, siguiendo la inclinación de la regla).
3. Indicar cuánto vale **1 división** (por defecto `1 mm`); la escala
   **µm/píxel** se calcula sola. El botón **Detectar de nuevo** reintenta.

**Pestaña 2 · Análisis (gráfico)**

1. **Cargar archivo de gotas**.
2. Imagen anotada a la izquierda, **histograma** a la derecha.
3. Sliders **Oscuridad** y **Enfoque** (re-analizan al soltar, con pantalla de
   carga).
4. **Zoom**: rueda del mouse (centrado en el cursor), botones **+ / − / Ajustar**
   y arrastrar para mover (con límite para que la imagen nunca deje hueco vacío).
5. Estadísticas: **gotas reconocidas, tamaño promedio y desviación estándar**
   (en µm si se calibró, o en píxeles si no).

---

## 3. Backend — Cálculos y variables

Lógica en `detector.py`: cómo se calibra la escala (píxeles → cm → µm) y cómo se
detectan y miden las gotas.

### 3.1 Calibración cm/mm → µm por píxel

Objetivo: convertir tamaños de **píxeles** a **µm**. Se necesita saber cuántos
micrómetros representa cada píxel (`um_per_pixel`), obtenido de la foto de la
regla.

#### Detección automática de la separación de las marcas

Función: `detect_ruler_spacing(image_path, max_dim=1400)`.

1. **Reducción de tamaño**: lado mayor llevado a `max_dim = 1400 px`, factor
   `f = max_dim / max(alto, ancho)`. Al final la separación se reescala
   dividiendo por `f`.
2. **Realce de contraste (CLAHE)**: `clipLimit=3.0`, `tileGridSize=(8,8)`.
   Resalta marcas tenues.
3. **Búsqueda del ángulo de inclinación (shear)**: se prueban cizallamientos
   `sh` de **-0.6 a 0.6** (≈ ±31°) en pasos de 0.04:
   - Marcas horizontales (regla vertical): `y' = sh·x + y`.
   - Marcas verticales (regla horizontal): `x' = x + sh·y`.
   El ángulo correcto alinea las marcas y maximiza la periodicidad.
4. **Análisis por bandas**: bandas perpendiculares a las marcas
   (`band_w = max(30, perp/20)`, paso `band_w/2`), cada una promediada a un
   perfil 1D.
5. **Periodicidad por autocorrelación** (`_analyze_band`):
   - Se quita la tendencia de iluminación: `detr = perfil − suavizado`.
   - `energy = desviación estándar del perfil` (contraste de la banda).
   - La **autocorrelación** da el primer pico fuerte: su posición es el
     **periodo** (separación entre marcas) y su altura la **confianza** (0–1).
   - `score = confianza × energy` → prioriza bandas periódicas **y** con
     contraste (la regla), descartando zonas lisas o en blanco.
6. **Refinamiento fino del ángulo**: alrededor del mejor `sh` se prueba un rango
   más fino (±0.04 en pasos de 0.008) sobre la banda elegida.
7. **Separación y confianza finales** (`_refine_ticks`):
   - `spacing` = **mediana** de las separaciones consecutivas entre marcas
     (más robusta que el periodo entero de la autocorrelación).
   - `regularity = 1 − (desviación estándar / media)` de esas separaciones:
     mide qué tan parejas están las marcas (confianza más intuitiva).
   - `confidence = max(regularity, confianza_autocorrelación)`.

Devuelve: `spacing_px`, `orientation`, `angle_deg`, `confidence` y
`tick_segments` (para dibujar las marcas).

#### Cálculo de µm por píxel

En `app.py`, una vez detectada la separación:

```
um_per_pixel = (valor_division × UNIT_TO_UM[unidad]) / spacing_px
```

| Variable         | Significado                                               |
|------------------|----------------------------------------------------------|
| `valor_division` | Cuánto vale una marca de la regla (lo escribe el usuario) |
| `unidad`         | `"mm"` o `"cm"`                                           |
| `UNIT_TO_UM`     | `{"mm": 1000, "cm": 10000}` (µm por unidad)              |
| `spacing_px`     | Separación detectada entre marcas, en píxeles            |

**Ejemplo**: marcas a `spacing_px = 50` px y una división de `1 mm`:
`um_per_pixel = (1 × 1000) / 50 = 20 µm/píxel`.

### 3.2 Detección y medición de gotas

Función: `analyze_image(image_path, darkness_pct, focus_pct, um_per_pixel, ...)`.

#### Parámetros controlables (sliders)

| Slider    | Variable interna | Efecto |
|-----------|------------------|--------|
| **Oscuridad** (`darkness_pct`, 0–100) | `black_threshold = darkness_pct × 2.55` | Umbral de "negro": qué tan oscuro debe ser un píxel para contar como gota. |
|           | `border_darkness_threshold = (darkness_pct + 9) × 2.55` | Umbral del borde (9% más claro que el núcleo). |
| **Enfoque** (`focus_pct`, 0–100) | `min_core_ratio = focus_pct / 100` | Proporción mínima del contorno que debe ser núcleo bien oscuro/enfocado. |

(El factor `2.55` convierte un porcentaje 0–100 a la escala 0–255 de la imagen.)

#### Parámetros fijos

| Variable          | Valor   | Significado                                     |
|-------------------|---------|-------------------------------------------------|
| `min_area`        | 5 px    | Área mínima del contorno (descarta ruido).      |
| `max_area`        | 1000 px | Área máxima (descarta manchas grandes no-gota). |
| `min_aspect`      | 0.5     | Relación ancho/alto mínima del bounding box.    |
| `max_aspect`      | 5.0     | Relación ancho/alto máxima.                     |
| `min_circularity` | 0.8     | Circularidad mínima (1 = círculo perfecto).     |

#### Procesamiento

1. **Escala de grises** y **desenfoque gaussiano** `(7,7)`.
2. **Umbralización inversa** (`THRESH_BINARY_INV`): los píxeles oscuros quedan
   en blanco. Dos máscaras: `core_thresh` (con `black_threshold`) y
   `border_thresh` (con `border_darkness_threshold`).
3. **Contornos** sobre `border_thresh` (`findContours`, `RETR_LIST`), para
   medir el ancho completo de la gota. `core_thresh` se usa después para
   validar qué proporción del contorno corresponde al núcleo oscuro.
4. Para cada contorno se **filtra**:
   - **Área**: `min_area < area < max_area`.
   - **Aspecto**: `min_aspect < w/h < max_aspect`.
   - **Circularidad**: `4·π·area / perímetro² ≥ min_circularity`.
   - **Núcleo**: `core_ratio = core_pixels / area ≥ min_core_ratio`.
   - Si pasa todos, la gota es válida.

#### Medición y estadísticas

- Se guarda el **ancho** `w` de cada gota (px).
- Conversión (si hay calibración): `ancho_µm = w × um_per_pixel`; si no, en px.
- `count` (cantidad), `mean_width` (promedio), `std_width` (desviación estándar).

#### Salidas principales

| Clave            | Contenido                                            |
|------------------|------------------------------------------------------|
| `count`          | Cantidad de gotas detectadas.                        |
| `widths`         | Lista de anchos (µm o px según calibración).         |
| `mean_width`     | Ancho promedio.                                      |
| `std_width`      | Desviación estándar de los anchos.                   |
| `unit`           | `"µm"` (calibrado) o `"px"` (sin calibrar).          |
| `output_rgb`     | Imagen con cajas verdes y el ancho de cada gota.     |
| `debug_rgb`      | Imagen con los núcleos pintados de rojo.             |
| `total_contours` | Contornos iniciales antes de filtrar.                |
