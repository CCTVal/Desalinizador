# Desalinizador — Detección y medición de gotas por análisis de imagen

Detecta y mide el diámetro de gotas en suspensión a partir de fotografías de la cámara de humidificación del desalinizador solar.  
Basado en el método de **Blaisot (ICLASS 2012)**: _"Drop Size and Drop Size Distribution Measurements by Image Analysis"_.

Cualquier duda, dirigirla a Sebastián Vidal, coordinador de este desarrollo.

---

## Requisitos

```bash
pip install numpy opencv-python matplotlib
# Para imágenes RAW (opcional):
pip install rawpy imageio
```

---

## Uso

```bash
python3 gotas.py <ruta_imagen>
```

**Ejemplo:**
```bash
python3 gotas.py DSC_0108.JPG
```

Acepta JPEG, PNG y formatos RAW (NEF, CR2, CR3, ARW, ORF, RW2, DNG).  
Si no se especifica imagen, usa `DSC_0111.JPG` por defecto.

### Archivos de salida

| Archivo | Contenido |
|---------|-----------|
| `<imagen>_new.jpg` | Imagen original con cuadros verdes sobre cada gota detectada y su diámetro en µm |
| `<imagen>_debug.jpg` | Imagen con los contornos detectados resaltados en rojo |
| `<imagen>_graficos.png` | 4 gráficos: histograma, CDF, mapa de posiciones y boxplot |

Al finalizar, los resultados se abren automáticamente en el visor de imágenes.

---

## Algoritmo — paso a paso

### Paso 1 · Detección del área iluminada

Se aplica un **blur Gaussiano de 501 px** sobre la imagen para obtener el mapa de iluminación suave. Los píxeles donde `illum > 80` corresponden a la zona iluminada real. Se erosiona ese mapa con un margen de `border_margin_px` para excluir el anillo oscuro del borde del círculo de luz.

```
illum     = GaussianBlur(gray, 501px)
illum_mask = illum > 80
inner_mask = erosion(illum_mask, margen=120px)
```

**Ventaja:** inmune a gotas oscuras dentro del área (el blur promedia sobre regiones grandes); no necesita detectar el círculo geométricamente.

---

### Paso 2 · Estimación del fondo y normalización

Se reutiliza el blur de 501 px como estimación del fondo local `I_back`. Esto permite detectar gotas de hasta ~3145 µm de diámetro sin contaminación (a diferencia del blur de 201 px que solo alcanzaba ~1257 µm).

La normalización sigue la **Ecuación 11 de Blaisot**:

```
Ĩ(i,j) = (I(i,j) − I_noise) / (I_back(i,j) − I_noise)
```

donde `I_noise` = percentil 1 de los píxeles iluminados (piso de ruido del sensor).

---

### Paso 3 · Mapa de diferencia y umbral adaptativo

```
diff = clip(I_back − I, 0, 255)
```

Valores positivos indican píxeles **más oscuros que el fondo local** → posible gota.

El umbral de detección es adaptativo:

```
thresh = max(diff_min, l_star × std(diff))
```

Se binariza `diff > thresh` y se aplica una apertura morfológica (kernel 3×3) para eliminar ruido puntual aislado.

---

### Paso 4 · Filtros por contorno

Para cada contorno detectado se aplican 5 filtros en cascada:

| Filtro | Criterio | Qué elimina |
|--------|----------|-------------|
| **Área** | `min_area < area < max_area` | Contornos demasiado pequeños o grandes |
| **Aspecto** | `0.4 < w/h < 2.5` | Formas muy alargadas |
| **Circularidad** | `4π·A/P² ≥ circ_min` | Formas irregulares, clusters |
| **Core darkness** | `(I_back_local − gray_p10) / I_back_local ≥ dark_fill_min` | Centros de anillos de Fresnel |
| **Contraste C₀** | `C₀ ≥ C_min` | Regiones con contraste insuficiente |

#### Filtro Core Darkness — el más importante

Distingue gotas reales de los **anillos de difracción de Fresnel** (la textura de burbujas del fondo):

```
core_dark = (I_back_local − gray_p10_interior) / I_back_local
```

donde `gray_p10_interior` es el percentil 10 del nivel de gris dentro del contorno relleno.

| Tipo de objeto | gray_p10 típico | core_dark típico |
|----------------|----------------|-----------------|
| Gota real in-focus | 90–150 | **0.32–0.58** ✓ |
| Centro de anillo Fresnel | 162–185 | **0.21–0.28** ✗ |

El umbral `dark_fill_min = 0.30` separa ambos casos. Es **normalizado** respecto a `I_back_local`, por lo que funciona correctamente aunque la iluminación varíe de 213 (borde) a 237 (centro) dentro de la imagen.

---

### Paso 5 · Medición

El diámetro equivalente de cada gota se calcula desde el área del contorno (**Ecuación de Blaisot**):

```
d_eq = 2 · √(A / π)        [en píxeles]
d_um = d_eq / px_per_um     [en micrómetros]
```

---

## Parámetros configurables

Todos los parámetros se encuentran al inicio de `gotas.py`:

### Calibración de escala

| Parámetro | Valor por defecto | Descripción |
|-----------|------------------|-------------|
| `px_per_mm` | `79.5` | Píxeles por milímetro. Calibrado con `referencia_Tamron.JPG`. **Si cambia la lente o distancia focal, recalibrar.** |

### Rango de tamaños

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `min_diameter_um` | `100` | Diámetro mínimo en µm. Bajarlo detecta gotas más pequeñas pero aumenta falsos positivos. |
| `max_diameter_um` | `4000` | Diámetro máximo en µm. |

### Detección

| Parámetro | Valor | Efecto al **subir** | Efecto al **bajar** |
|-----------|-------|--------------------|--------------------|
| `diff_min` | `40` | Menos gotas (solo las muy oscuras) | Más gotas, más falsos positivos |
| `l_star` | `2.0` | Umbral adaptativo más alto | Más detecciones en zonas de bajo contraste |
| `dark_fill_min` | `0.30` | Solo gotas muy negras | Acepta gotas más grises y anillos Fresnel |
| `circularity_min` | `0.60` | Solo gotas casi circulares | Acepta formas irregulares |
| `C_min` | `0.07` | Solo alto contraste | Acepta bajo contraste |
| `border_margin_px` | `120` | Región de análisis más pequeña | Analiza más cerca del borde |

### Guía rápida de ajuste

```
Demasiados falsos positivos  → subir diff_min o dark_fill_min
Pocas gotas detectadas       → bajar diff_min o dark_fill_min
Detecta formas raras         → subir circularity_min
No detecta gotas pequeñas    → bajar min_diameter_um
```

---

## Calibración de escala (`px_per_mm`)

Para recalibrar con una nueva imagen de referencia:

```python
# Medir cuántos píxeles ocupa una distancia conocida en la imagen
px_per_mm = pixeles_medidos / mm_conocidos
# Ejemplo: marca de 10 mm ocupa 795 px → px_per_mm = 79.5
```

---

## Resultados en DSC_0108.JPG

Con la configuración por defecto (`diff_min=40`, `dark_fill_min=0.30`):

| Métrica | Valor |
|---------|-------|
| Gotas detectadas | 16 |
| Diámetro medio | 149.2 µm |
| Mediana | 127.5 µm |
| Rango | 101 – 301 µm |
| Contraste C₀ medio | 1.000 |
| Área iluminada analizada | 794 mm² |

---

## Cambios respecto a la versión original

### 1. Detección del área iluminada — nueva estrategia robusta

**Problema:** Se usaba `HoughCircles` o `minEnclosingCircle` para encontrar el círculo de iluminación. Fallaba cuando el círculo se salía de los bordes de la imagen, generando una máscara demasiado grande que incluía zonas oscuras del fondo, lo que producía miles de falsos positivos.

**Solución:** Se usa el blur de 501 px como mapa de iluminación directamente. Solo se considera zona iluminada donde `illum > 80`, luego se erosiona con `border_margin_px`. Funciona aunque el círculo esté parcialmente fuera de la imagen.

---

### 2. Estimación del fondo — blur 501 px en lugar de 201 px

**Problema:** Con `I_back = GaussianBlur(gray, 201px)` (sigma ≈ 33 px), para gotas con radio > 33 px la estimación del fondo se contamina con el propio blob, reduciendo `diff` a casi 0 y dejando esas gotas sin detectar.

**Solución:** Se reutiliza `illum` (blur 501 px, sigma ≈ 83 px) como `I_back`. Un solo cálculo sirve para ambos propósitos (máscara + fondo), sin costo computacional extra.

| Blur | Sigma | Radio máximo detectable |
|------|-------|------------------------|
| 201 px | ~33 px | ~100 px = 1257 µm |
| **501 px** | **~83 px** | **~250 px = 3145 µm** |

---

### 3. Filtro `core_dark` — reemplaza `fill_fraction`

**Problema:** El filtro `fill_fraction` original era ineficaz: contaba píxeles con `diff > thresh/2` dentro del contorno. Como todos los píxeles del contorno ya tienen `diff > thresh > thresh/2` por construcción, el fill era siempre 1.0 para cualquier contorno y no filtraba nada.

**Solución:** Nuevo filtro `core_dark` que mide qué tan oscuro es el núcleo de la gota en términos normalizados:

```python
core_dark = (I_back_local − gray_p10_interior) / I_back_local
```

- **Gotas reales:** `core_dark ≈ 0.32–0.58` (núcleo claramente oscuro)
- **Anillos de Fresnel:** `core_dark ≈ 0.21–0.28` (centro gris, similar al fondo)

El umbral `0.30` elimina los falsos positivos de la textura de burbujas sin perder gotas reales. La normalización por `I_back_local` lo hace robusto ante la variación de iluminación dentro de la imagen.

**Resultado en DSC_0108.JPG:** de 39 detecciones (23 falsas) a 16 detecciones (todas C₀ = 1.000).

---

### 4. Apertura automática de resultados sin DISPLAY manual

**Problema:** En sistemas Linux sin variable `DISPLAY` configurada (e.g. terminales remotas), `xdg-open` fallaba silenciosamente.

**Solución:** Se detecta el display activo automáticamente:

```python
sockets = glob.glob("/tmp/.X11-unix/X*")
env["DISPLAY"] = ":" + sockets[0].replace("/tmp/.X11-unix/X", "")
```

---

## Estructura del repositorio

```
Desalinizador/
├── gotas.py     # Script principal de detección
└── README.md    # Esta documentación
```

---

## Referencias

- Blaisot, J.B. (2012). *Drop Size and Drop Size Distribution Measurements by Image Analysis*. ICLASS 2012, 12th Triennial International Conference on Liquid Atomization and Spray Systems.
