"""
Detección y medición de gotas por análisis de imagen.
Basado en: Blaisot, J.B. (ICLASS 2012) - "Drop Size and Drop Size Distribution
           Measurements by Image Analysis"

Técnicas implementadas:
  - Normalización de imagen (Ec. 11): Ĩ = (I - I_noise) / (I_back - I_noise)
  - Contraste normalizado C₀ por gota
  - Nivel de referencia l* adaptativo según C₀
  - Diámetro equivalente desde área: d = 2·√(A/π)
  - Filtro por contraste mínimo C_min
"""

import numpy as np
import cv2
from sys import argv
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import subprocess

# ─────────────────────────────────────────────────────────────────────────────
# PARÁMETROS — ajustar según el setup óptico
# ─────────────────────────────────────────────────────────────────────────────

# Escala (medida con referencia_Tamron.JPG, marcas en cm)
px_per_mm = 79.5            # píxeles por milímetro
px_per_um = px_per_mm / 1000.0

# Rango de tamaño de gotas a detectar (µm)
min_diameter_um = 100   # diámetro mínimo de gota a detectar
max_diameter_um = 4000  # blobs grandes out-of-focus pueden ser > 1500µm

# ── Detección de oscuridad relativa al fondo local ───────────────────────────
# l_star: multiplica el std del mapa diff → umbral adaptativo
l_star = 2.0            # 1.5–3.0 es rango razonable

# Umbral MÍNIMO de diff: gota debe ser al menos este número de niveles más oscura
# que su fondo local.
# - Gotas pequeñas in-focus (muy oscuras): diff ≈ 50–143
# - Blobs grandes out-of-focus (gris oscuro): diff ≈ 15–50
# - Anillos de Fresnel / textura pura: diff ≈ 5–15
diff_min = 40           # solo gotas claramente oscuras (diff ≈ 40–143)

# Oscuridad normalizada del NÚCLEO del contorno:
#   core_dark = (I_back_local − gray_p10_interior) / I_back_local
#   Gota real in-focus:       gray_p10 ≈ 90–155 → core_dark ≈ 0.32–0.58  ✓
#   Centro de anillo Fresnel: gray_p10 ≈ 162–185 → core_dark ≈ 0.21–0.28  ✗
# Umbral 0.30 separa ambos casos robustamente (sin depender del nivel absoluto
# de iluminación, que varía de ≈213 en el borde a ≈237 en el centro).
dark_fill_min = 0.30    # fracción normalizada (0–1)

# Filtro de circularidad — 1.0 = círculo perfecto
circularity_min = 0.60

# Filtro de contraste (Blaisot Ec. 8)
C_min = 0.07

# Detección del círculo de iluminación
border_margin_px = 120

# ─────────────────────────────────────────────────────────────────────────────

def normalizar_imagen(imagen_gray, radio_fondo=51):
    """
    Normalización tipo Blaisot Ec. 11:
        Ĩ(i,j) = (I(i,j) - I_noise) / (I_back(i,j) - I_noise)

    Sin imagen de fondo dedicada, se estima I_back con blur fuerte (fondo local).
    I_noise = percentil 1 de la imagen (ruido oscuro del sensor).
    """
    I_noise = float(np.percentile(imagen_gray, 1))      # ruido sensor
    I_back  = cv2.GaussianBlur(                         # fondo local estimado
        imagen_gray.astype(np.float32),
        (radio_fondo, radio_fondo), 0
    )
    # Evitar división por cero
    denominador = I_back - I_noise
    denominador[denominador < 1] = 1

    I_norm = (imagen_gray.astype(np.float32) - I_noise) / denominador
    I_norm = np.clip(I_norm, 0.0, 1.0)
    return I_norm, I_back, I_noise


def contraste_normalizado(I_norm_region):
    """
    Contraste normalizado C₀ (Blaisot Ec. 8):
        C  = h / (i_max + i_min)   donde h = i_max - i_min
        C₀ = C / ((1 - τ)(1 + C) - C)   con τ ≈ 0 (objeto opaco)
    Para τ≈0: C₀ = C (simplificación válida para gotas de agua opacas).
    """
    i_max = float(np.max(I_norm_region))
    i_min = float(np.min(I_norm_region))
    if (i_max + i_min) < 1e-6:
        return 0.0
    C = (i_max - i_min) / (i_max + i_min)
    return C


# ─────────────────────────────────────────────────────────────────────────────
# CARGA DE IMAGEN (acepta NEF/RAW y JPEG/PNG)
# ─────────────────────────────────────────────────────────────────────────────
try:
    image_path = argv[1]
except IndexError:
    image_path = "DSC_0111.JPG"
    print("No image filename received. Will use default value: " + image_path)

raw_extensions = {".nef", ".cr2", ".cr3", ".arw", ".orf", ".rw2", ".dng"}
ext = os.path.splitext(image_path)[1].lower()

if ext in raw_extensions:
    try:
        import rawpy, imageio
        jpg_path = os.path.splitext(image_path)[0] + "_raw.jpg"
        print(f"Convirtiendo RAW → JPG: {image_path}")
        with rawpy.imread(image_path) as raw:
            rgb = raw.postprocess(use_camera_wb=True, output_bps=8, no_auto_bright=False)
        imageio.imwrite(jpg_path, rgb)
        image_path = jpg_path
        print("Conversión completada ✓\n")
    except ImportError:
        print("⚠️  Instalar: pip install rawpy imageio")
        exit(1)

image = cv2.imread(image_path)
if image is None:
    print(f"Error: no se pudo cargar '{image_path}'")
    exit(1)

gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
h, w = gray.shape

# Conversión de rango a píxeles
min_diam_px = min_diameter_um * px_per_um
max_diam_px = max_diameter_um * px_per_um
min_area_px = np.pi * (min_diam_px / 2) ** 2
max_area_px = np.pi * (max_diam_px / 2) ** 2

print(f"Escala: {px_per_mm:.1f} px/mm  |  Rango: {min_diameter_um}–{max_diameter_um} µm")
print(f"  → {min_diam_px:.1f}–{max_diam_px:.1f} px de diámetro")
print(f"  → l*={l_star}  |  diff_min={diff_min}  |  core_dark≥{dark_fill_min:.2f}  |  C₀≥{C_min}\n")

# ─────────────────────────────────────────────────────────────────────────────
# 1. DETECCIÓN DEL ÁREA ILUMINADA
#
#    Estrategia robusta: blur muy grande (501px) para estimar el nivel de
#    iluminación en cada punto. Donde illum > umbral = zona illuminada real.
#    Luego erosión para excluir el anillo oscuro del borde.
#
#    Ventaja: inmune a gotas oscuras (el blur promedia sobre áreas grandes),
#             no depende de detección de círculo (que puede ser imprecisa si
#             el círculo se sale de los bordes de la imagen).
# ─────────────────────────────────────────────────────────────────────────────
illum = cv2.GaussianBlur(gray.astype(np.float32), (501, 501), 0)
_, illum_mask = cv2.threshold(illum.astype(np.uint8), 80, 255, cv2.THRESH_BINARY)

k_erode = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (border_margin_px*2+1, border_margin_px*2+1))
inner_mask = cv2.erode(illum_mask, k_erode, iterations=1)

# Para visualización: encontrar contorno y círculo estimado
cnts_illum, _ = cv2.findContours(inner_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
big_circle_cnt = max(cnts_illum, key=cv2.contourArea) if cnts_illum else None
if big_circle_cnt is not None:
    (cx, cy), radius = cv2.minEnclosingCircle(big_circle_cnt)
    cx, cy, radius = int(cx), int(cy), int(radius)
else:
    cx, cy, radius = w//2, h//2, min(w,h)//2

inner_mask_area = int(np.sum(inner_mask == 255))
print(f"Área iluminada (sin borde): {inner_mask_area} px = {inner_mask_area/(px_per_mm**2):.0f} mm²")
print(f"Círculo aprox: centro=({cx},{cy}), radio={radius}px = {radius/px_per_mm:.1f}mm")

# ─────────────────────────────────────────────────────────────────────────────
# 2. IMAGEN DE FONDO Y NORMALIZACIÓN (Blaisot Ec. 11)
# ─────────────────────────────────────────────────────────────────────────────
I_noise = float(np.percentile(gray, 1))
gray_inner = gray.copy().astype(np.float32)
gray_inner[inner_mask == 0] = 0   # píxeles fuera de la región de análisis → 0

# Blur para estimar fondo local.
# REGLA: para detectar un blob de radio R correctamente, el sigma del blur debe
# ser >> R. Con kernel ksize, sigma ≈ 0.3*(ksize/2-1)+0.8.
#   ksize=201 → sigma≈33px → detecta gotas hasta radio≈100px (1257µm)
#   ksize=501 → sigma≈83px → detecta gotas hasta radio≈250px (3145µm)  ← MEJOR
#
# Reutilizamos illum (ya calculado arriba, 501px) para no calcular dos veces.
# Esto permite detectar gotas grandes out-of-focus (1000–4000µm) que el blur
# de 201px no detectaba por contaminación (blob radius >> sigma).
I_back = illum.copy()
I_back[inner_mask == 0] = 0   # igual que gray_inner: cero fuera de análisis

# Normalizar para cálculo posterior de C₀
I_noise_f = float(np.percentile(gray[inner_mask == 255], 1))
denom = np.clip(I_back - I_noise_f, 1, None)
I_norm = np.clip((gray.astype(np.float32) - I_noise_f) / denom, 0.0, 1.0)

# ─────────────────────────────────────────────────────────────────────────────
# 3. DETECCIÓN: DIFERENCIA RELATIVA AL FONDO + FILL FRACTION
#
#    diff = I_back - I  → positivo donde hay gota (más oscuro que fondo local)
#    Umbral adaptativo: thresh = max(diff_min, l_star × std(diff))
#
#    Ventajas vs umbral absoluto:
#      - funciona aunque el fondo no sea uniforme
#      - insensible a la zona oscura periférica (fondo también oscuro → diff≈0)
#
#    Luego se aplica filtro de FILL FRACTION para eliminar anillos de Fresnel:
#      - Gota sólida: interior de contorno mayormente oscuro vs fondo → fill alto
#      - Anillo de Fresnel: interior claro (igual que fondo) → fill bajo → RECHAZADO
# ─────────────────────────────────────────────────────────────────────────────
diff = np.clip(I_back - gray_inner, 0, 255).astype(np.uint8)
diff_masked = cv2.bitwise_and(diff, inner_mask)

interior_vals = diff_masked[inner_mask == 255]
thresh_val = max(diff_min, int(l_star * float(np.std(interior_vals))))
print(f"Umbral diff: {thresh_val} px  (l*={l_star} × std={np.std(interior_vals):.1f})"
      f"  |  core_dark mín: {dark_fill_min:.2f}")

_, drops_bin = cv2.threshold(diff_masked, thresh_val, 255, cv2.THRESH_BINARY)

# OPEN: elimina puntos aislados de ruido (no CLOSE para no unir gotas separadas)
k_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
drops_bin = cv2.morphologyEx(drops_bin, cv2.MORPH_OPEN, k_open, iterations=1)

# RETR_EXTERNAL: solo contorno externo de cada región.
# Para anillos de Fresnel: el contorno externo rodea el anillo + centro brillante
# → al medir fill, el centro brillante "diluye" la fracción oscura → rechazado
contours, _ = cv2.findContours(drops_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
print(f"Contornos iniciales: {len(contours)}")

# ─────────────────────────────────────────────────────────────────────────────
# 4. FILTRADO Y MEDICIÓN DE GOTAS
# ─────────────────────────────────────────────────────────────────────────────
detected = []
output_image = image.copy()
debug_image  = image.copy()
# Dibujar contorno del área de análisis
cv2.drawContours(output_image, [big_circle_cnt], -1, (255, 128, 0), 3)

rechazados = {"area": 0, "aspecto": 0, "circularidad": 0, "fill": 0, "contraste": 0}

for contour in contours:
    area_px = cv2.contourArea(contour)
    x, y, wb, hb = cv2.boundingRect(contour)

    # ── Filtro de área ────────────────────────────────────────────────────────
    if not (min_area_px < area_px < max_area_px):
        rechazados["area"] += 1
        continue

    # ── Filtro de relación de aspecto ─────────────────────────────────────────
    aspect = float(wb) / hb if hb > 0 else 0
    if not (0.4 < aspect < 2.5):
        rechazados["aspecto"] += 1
        continue

    # ── Filtro de circularidad ────────────────────────────────────────────────
    perimeter = cv2.arcLength(contour, True)
    if perimeter == 0:
        continue
    circularity = (4 * np.pi * area_px) / (perimeter ** 2)
    if circularity < circularity_min:
        rechazados["circularidad"] += 1
        continue

    # ── FILTRO CLAVE: oscuridad del NÚCLEO (p10 del gris interior) ───────────
    #
    # Problema: los centros de anillos de Fresnel tienen gris~165-185 y apenas
    # pasan el umbral diff_min. Una gota real in-focus tiene gris~80-140 en su
    # interior (al menos el 10% de los píxeles son muy oscuros).
    #
    # core_diff = I_back_local − gray_p10_interior
    #   → gota real   : I_back≈213, gray_p10≈90–150 → core_diff ≈ 63–123  ✓
    #   → anillo Fresnel: I_back≈213, gray_p10≈162–185 → core_diff ≈ 28–51  ✗
    #
    # Umbral: core_diff_min (ajustable; 55 separa bien ambos casos)
    #
    mask_tmp = np.zeros((h, w), dtype=np.uint8)
    cv2.drawContours(mask_tmp, [contour], -1, 255, -1)   # contorno relleno
    gray_dentro  = gray.astype(np.float32)[mask_tmp == 255]
    I_back_local = float(np.mean(I_back[mask_tmp == 255]))
    if len(gray_dentro) == 0:
        continue
    gray_p10_local = float(np.percentile(gray_dentro, 10))
    # Oscuridad normalizada: fracción de la intensidad de fondo que es "más oscuro"
    # Independiente del nivel absoluto de iluminación (varía 213–237 en esta imagen)
    core_dark = (I_back_local - gray_p10_local) / max(I_back_local, 1.0)
    if core_dark < dark_fill_min:
        rechazados["fill"] += 1
        continue

    # ── Contraste normalizado C₀ (Blaisot Ec. 8) ─────────────────────────────
    margin = max(3, int(max(wb, hb) * 0.3))
    x1 = max(0, x - margin);  y1 = max(0, y - margin)
    x2 = min(w, x + wb + margin); y2 = min(h, y + hb + margin)
    region_norm = I_norm[y1:y2, x1:x2]
    C0 = contraste_normalizado(region_norm)

    if C0 < C_min:
        rechazados["contraste"] += 1
        continue

    # ── Diámetro equivalente desde área (Blaisot: d = 2·√(A/π)) ─────────────
    diam_eq_px = 2.0 * np.sqrt(area_px / np.pi)
    diam_eq_um = diam_eq_px / px_per_um

    detected.append({
        "x": x, "y": y, "w": wb, "h": hb,
        "area_px":    area_px,
        "diam_eq_um": diam_eq_um,
        "C0":         C0,
        "circularity": circularity,
        "core_dark":  core_dark,
    })

    # Visualización
    color = (0, 255, 0)
    cv2.rectangle(output_image, (x, y), (x+wb, y+hb), color, 2)
    cv2.putText(output_image, f"{diam_eq_um:.0f}um",
                (x, y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1)

    mask_dbg = np.zeros((h, w), dtype=np.uint8)
    cv2.drawContours(mask_dbg, [contour], -1, 255, -1)
    debug_image[mask_dbg == 255] = (0, 0, 255)

# ─────────────────────────────────────────────────────────────────────────────
# 5. RESULTADOS
# ─────────────────────────────────────────────────────────────────────────────
n = len(detected)
print(f"\nGotas rechazadas por filtro:")
for k_r, v_r in rechazados.items():
    print(f"  {k_r:15s}: {v_r}")

if n > 0:
    diams  = np.array([d["diam_eq_um"] for d in detected])
    c0s    = np.array([d["C0"]         for d in detected])

    print(f"\n✅ Gotas detectadas: {n}")
    print(f"   Diámetro equiv. medio:  {np.mean(diams):.1f} µm  (±{np.std(diams):.1f} µm)")
    print(f"   Mediana:                {np.median(diams):.1f} µm")
    print(f"   Rango:                  {np.min(diams):.1f} – {np.max(diams):.1f} µm")
    print(f"   Contraste C₀ medio:     {np.mean(c0s):.3f}  (±{np.std(c0s):.3f})")

    # Guardar imágenes segmentadas
    out_jpg   = image_path + "_new.jpg"
    debug_jpg = image_path + "_debug.jpg"
    cv2.imwrite(out_jpg,   output_image)
    cv2.imwrite(debug_jpg, debug_image)

    # ── Gráficos (4 paneles) ─────────────────────────────────────────────────
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(
        f"Análisis de gotas — {os.path.basename(image_path)}\n"
        f"N={n}  |  Media={np.mean(diams):.1f} µm  |  "
        f"Mediana={np.median(diams):.1f} µm  |  "
        f"Rango={np.min(diams):.0f}–{np.max(diams):.0f} µm  |  "
        f"Método: Blaisot 2012",
        fontsize=11, fontweight='bold'
    )

    # 1. Histograma
    ax1 = axes[0, 0]
    bins = np.arange(diams.min(), diams.max() + 10, 10)
    ax1.hist(diams, bins=bins, color='steelblue', edgecolor='white', lw=0.5)
    ax1.axvline(np.mean(diams),   color='red',    ls='--', lw=1.5, label=f'Media: {np.mean(diams):.1f} µm')
    ax1.axvline(np.median(diams), color='orange', ls='--', lw=1.5, label=f'Mediana: {np.median(diams):.1f} µm')
    ax1.set_xlabel('Diámetro equivalente (µm)')
    ax1.set_ylabel('N° de gotas')
    ax1.set_title('Histograma de diámetros')
    ax1.legend(); ax1.grid(axis='y', alpha=0.3)

    # 2. CDF
    ax2 = axes[0, 1]
    sorted_d = np.sort(diams)
    cdf = np.arange(1, n+1) / n * 100
    ax2.plot(sorted_d, cdf, color='steelblue', lw=2)
    for pct, col in [(25,'orange'), (50,'red'), (75,'green')]:
        val = np.percentile(diams, pct)
        ax2.axvline(val, color=col, ls=':', lw=1.2, label=f'P{pct}: {val:.1f} µm')
    ax2.set_xlabel('Diámetro equivalente (µm)')
    ax2.set_ylabel('% acumulado')
    ax2.set_title('Distribución acumulada (CDF)')
    ax2.legend(); ax2.grid(alpha=0.3)

    # 3. Mapa de posiciones coloreado por diámetro
    ax3 = axes[1, 0]
    xs = [d["x"] + d["w"]//2 for d in detected]
    ys = [d["y"] + d["h"]//2 for d in detected]
    sc = ax3.scatter(xs, ys, c=diams, cmap='plasma', s=6, alpha=0.6,
                     vmin=diams.min(), vmax=diams.max())
    plt.colorbar(sc, ax=ax3, label='Diámetro (µm)')
    ax3.set_xlim(0, w); ax3.set_ylim(h, 0)
    ax3.set_xlabel('X (px)'); ax3.set_ylabel('Y (px)')
    ax3.set_title('Mapa de posiciones de gotas')
    ax3.set_aspect('equal'); ax3.grid(alpha=0.2)

    # 4. Boxplot
    ax4 = axes[1, 1]
    ax4.boxplot(diams, vert=True, patch_artist=True,
                boxprops=dict(facecolor='steelblue', alpha=0.6),
                medianprops=dict(color='red', lw=2),
                flierprops=dict(marker='o', ms=3, alpha=0.4))
    ax4.set_ylabel('Diámetro equivalente (µm)')
    ax4.set_title('Boxplot de diámetros')
    stats = (f"Media:   {np.mean(diams):.1f} µm\n"
             f"Mediana: {np.median(diams):.1f} µm\n"
             f"Std:     {np.std(diams):.1f} µm\n"
             f"Q1:      {np.percentile(diams,25):.1f} µm\n"
             f"Q3:      {np.percentile(diams,75):.1f} µm\n"
             f"C₀ med:  {np.mean(c0s):.3f}")
    ax4.text(1.32, np.median(diams), stats, fontsize=9, va='center',
             bbox=dict(boxstyle='round', fc='lightyellow', alpha=0.8))
    ax4.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    graficos_png = image_path + "_graficos.png"
    plt.savefig(graficos_png, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"\nArchivos guardados:")
    print(f"  → {out_jpg}")
    print(f"  → {debug_jpg}")
    print(f"  → {graficos_png}")

    # Abrir resultados (detectar display automáticamente)
    print("\nAbriendo resultados...")
    env = os.environ.copy()
    if not env.get("DISPLAY"):
        # Buscar display activo en /tmp/.X11-unix/
        import glob
        sockets = sorted(glob.glob("/tmp/.X11-unix/X*"))
        if sockets:
            env["DISPLAY"] = ":" + sockets[0].replace("/tmp/.X11-unix/X", "")
    for f in [out_jpg, graficos_png]:
        subprocess.Popen(["xdg-open", f],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         env=env)
else:
    print("\n⚠️  No se detectaron gotas. Sugerencias:")
    print(f"  • Baja diff_min (actual: {diff_min}) — prueba 10–15")
    print(f"  • Baja dark_fill_min (actual: {dark_fill_min}) — prueba 0.55–0.65")
    print(f"  • Baja C_min (actual: {C_min}) — prueba 0.04–0.06")
    print(f"  • Amplía el rango: min_diameter_um={min_diameter_um} / max_diameter_um={max_diameter_um}")
