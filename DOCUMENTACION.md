# Documentación del backend — Cálculos y variables

Este documento describe la lógica de [detector.py](detector.py): cómo se
calibra la escala (píxeles → cm → µm) y cómo se detectan y miden las gotas.

---

## 1. Calibración de la escala (cm / mm → µm por píxel)

Objetivo: convertir tamaños medidos en **píxeles** a unidades reales (**µm**).
Para eso se necesita saber cuántos micrómetros representa cada píxel
(`um_per_pixel`). Esto se obtiene de la foto de la **regla**.

### 1.1 Detección automática de la separación de las marcas

Función: `detect_ruler_spacing(image_path, max_dim=900)`.

Pasos:

1. **Reducción de tamaño**: se reescala la imagen para que su lado mayor sea
   `max_dim = 900 px`, con factor `f = max_dim / max(alto, ancho)`. Acelera el
   cálculo. Al final la separación se reescala de vuelta dividiendo por `f`.
2. **Realce de contraste (CLAHE)**: `clipLimit=2.0`, `tileGridSize=(8,8)`.
   Resalta marcas tenues sin saturar zonas brillantes.
3. **Búsqueda del ángulo de inclinación (shear)**: la regla suele estar algo
   torcida. Se prueban cizallamientos `sh` de **-0.16 a 0.16** (≈ ±9°) en pasos
   de 0.02. Cada `sh` aplica una transformación afín:
   - Marcas horizontales (regla vertical): `y' = sh·x + y`.
   - Marcas verticales (regla horizontal): `x' = x + sh·y`.
   El ángulo correcto alinea las marcas y maximiza la periodicidad.
4. **Análisis por bandas**: para cada orientación se recorre la imagen en
   bandas perpendiculares a las marcas (ancho `band_w = perp/6`, paso
   `band_w/2`). Cada banda se promedia a un perfil 1D.
5. **Periodicidad por autocorrelación** (`_analyze_band`):
   - Se quita la tendencia de iluminación con una media móvil
     (`detr = perfil − suavizado`).
   - `energy = desviación estándar del perfil` (contraste de la banda).
   - Se calcula la **autocorrelación** y se busca el primer pico fuerte: su
     posición es el **periodo** (separación entre marcas) y su altura la
     **confianza** (0–1).
   - `score = confianza × energy` → prioriza bandas que son periódicas **y**
     tienen contraste (la regla real), descartando zonas lisas o en blanco.
6. **Refinamiento fino del ángulo**: alrededor del mejor `sh` se prueba un
   rango más fino (paso 0.005 ≈ 0.3°) sobre la banda elegida.
7. **Separación y confianza finales** (`_refine_ticks`):
   - Se detectan las posiciones de las marcas (mínimos prominentes del perfil).
   - `spacing` = **mediana** de las separaciones consecutivas (robusta, mejor
     que el periodo entero de la autocorrelación).
   - `regularity = 1 − (desviación estándar / media)` de esas separaciones:
     mide qué tan parejas están las marcas. Es la **confianza** que se muestra
     (más intuitiva); se refuerza con la autocorrelación:
     `confidence = max(regularity, confianza_autocorrelación)`.

Devuelve: `spacing_px` (en escala original), `orientation`, `angle_deg`,
`confidence` y `tick_segments` (segmentos para dibujar las marcas detectadas).

### 1.2 Cálculo de µm por píxel

En la interfaz ([app.py](app.py)), una vez detectada la separación:

```
um_per_pixel = (valor_division × UNIT_TO_UM[unidad]) / spacing_px
```

donde:

| Variable          | Significado                                              |
|-------------------|---------------------------------------------------------|
| `valor_division`  | Cuánto vale una marca de la regla (lo escribe el usuario)|
| `unidad`          | `"mm"` o `"cm"`                                          |
| `UNIT_TO_UM`      | `{"mm": 1000, "cm": 10000}` (µm por unidad)             |
| `spacing_px`      | Separación detectada entre marcas, en píxeles           |

**Ejemplo**: si las marcas están a `spacing_px = 50` px y una división vale
`1 mm`:
`um_per_pixel = (1 × 1000) / 50 = 20 µm/píxel`.

---

## 2. Detección y medición de gotas

Función: `analyze_image(image_path, darkness_pct, focus_pct, um_per_pixel, ...)`.

### 2.1 Parámetros controlables (sliders)

| Slider      | Variable interna                              | Efecto |
|-------------|-----------------------------------------------|--------|
| **Oscuridad** (`darkness_pct`, 0–100) | `black_threshold = darkness_pct × 2.55`  | Umbral de "negro": qué tan oscuro debe ser un píxel para contar como gota. |
|             | `border_darkness_threshold = (darkness_pct + 9) × 2.55` | Umbral del borde (9% más claro que el núcleo, igual que el script original). |
| **Enfoque** (`focus_pct`, 0–100) | `min_core_ratio = focus_pct / 100` | Proporción mínima del contorno que debe ser núcleo bien oscuro/enfocado. |

(El factor `2.55` convierte un porcentaje 0–100 a la escala 0–255 de la imagen.)

### 2.2 Parámetros fijos

| Variable          | Valor    | Significado                                       |
|-------------------|----------|---------------------------------------------------|
| `min_area`        | 5 px     | Área mínima del contorno (descarta ruido).        |
| `max_area`        | 1000 px  | Área máxima (descarta manchas grandes no-gota).   |
| `min_aspect`      | 0.5      | Relación ancho/alto mínima del bounding box.      |
| `max_aspect`      | 5.0      | Relación ancho/alto máxima.                       |
| `min_circularity` | 0.8      | Circularidad mínima (1 = círculo perfecto).       |

### 2.3 Procesamiento

1. **Escala de grises** y **desenfoque gaussiano** `(7,7)` para suavizar.
2. **Umbralización inversa** (`THRESH_BINARY_INV`): los píxeles oscuros quedan
   en blanco. Se generan dos máscaras: `core_thresh` (con `black_threshold`) y
   `border_thresh` (con `border_darkness_threshold`).
3. **Contornos** sobre `border_thresh` (`findContours`, `RETR_LIST`), para
   medir el ancho completo de la gota. `core_thresh` se usa después para
   validar qué proporción del contorno corresponde al núcleo oscuro.
4. Para cada contorno se calcula y se **filtra**:
   - **Área**: `area = cv2.contourArea`, debe cumplir `min_area < area < max_area`.
   - **Bounding box** `(x, y, w, h)` y relación de aspecto `aspect = w/h`,
     debe cumplir `min_aspect < aspect < max_aspect`.
   - **Circularidad**: `circularity = 4·π·area / perímetro²`, debe ser
     `≥ min_circularity`.
   - **Núcleo (core)**: se cuenta cuántos píxeles dentro del contorno son
     "core" (muy oscuros) → `core_ratio = core_pixels / area`, debe ser
     `≥ min_core_ratio`.
   - Si pasa todos los filtros, la gota es válida.

### 2.4 Medición y estadísticas

- Para cada gota válida se guarda su **ancho** `w` (en píxeles).
- Conversión a unidades reales (si hay calibración):
  `ancho_µm = w × um_per_pixel`. Si no hay calibración, se reporta en píxeles.
- Estadísticas finales:
  - `count` = número de gotas reconocidas.
  - `mean_width` = promedio de los anchos.
  - `std_width` = desviación estándar de los anchos.

### 2.5 Salidas

| Clave          | Contenido                                                     |
|----------------|--------------------------------------------------------------|
| `count`        | Cantidad de gotas detectadas.                                |
| `widths`       | Lista de anchos (en µm o px según calibración).              |
| `mean_width`   | Ancho promedio.                                              |
| `std_width`    | Desviación estándar de los anchos.                          |
| `unit`         | `"µm"` (calibrado) o `"px"` (sin calibrar).                  |
| `output_rgb`   | Imagen con las cajas verdes y el ancho de cada gota.        |
| `debug_rgb`    | Imagen con los núcleos pintados de rojo.                     |
| `total_contours`| Contornos iniciales antes de filtrar.                      |
