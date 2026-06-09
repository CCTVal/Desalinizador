"""
Módulo de detección de gotas para el desalinizador.

Contiene la lógica de análisis de imágenes extraída de gotas.py,
refactorizada como una función reutilizable que admite:
  - Calibración (micrómetros por píxel) para entregar tamaños reales.
  - Parámetros de "Oscuridad" y "Enfoque" controlables desde sliders.
"""

import numpy as np
import cv2
from collections import Counter

# Colores (formato BGR de OpenCV)
RED_COLOR = (0, 0, 255)
GREEN_COLOR = (0, 255, 0)


def _imread(image_path, flags=cv2.IMREAD_COLOR):
    """Lee imagenes con rutas Windows no ASCII usando imdecode."""
    try:
        data = np.fromfile(image_path, dtype=np.uint8)
    except OSError:
        return None
    if data.size == 0:
        return None
    return cv2.imdecode(data, flags)


def _smooth(profile, k):
    """Suavizado por media móvil (sin dependencias externas)."""
    if k < 1:
        return profile
    kernel = np.ones(k) / k
    return np.convolve(profile, kernel, mode="same")


def _find_peaks(signal):
    """Índices de máximos locales de una señal 1D."""
    peaks = []
    for i in range(1, len(signal) - 1):
        if signal[i] > signal[i - 1] and signal[i] >= signal[i + 1]:
            peaks.append(i)
    return peaks


def _analyze_band(strip):
    """
    Analiza una banda 1D (perfil a lo largo del eje variable) y devuelve
    (periodo, confianza, score). El perfil debe ser el promedio de la banda.
    """
    n = len(strip)
    if n < 30:
        return None
    k = max(5, n // 40)
    detr = strip - _smooth(strip, k)
    detr -= detr.mean()
    energy = float(np.std(detr))
    if energy < 1e-6:
        return None

    m = 1 << int(np.ceil(np.log2(2 * n)))
    F = np.fft.rfft(detr, m)
    ac = np.fft.irfft(F * np.conj(F), m)[:n]
    if ac[0] <= 0:
        return None
    ac = ac / ac[0]
    lag_min = 4
    lag_max = max(lag_min + 1, n // 4)
    seg = ac[lag_min:lag_max]
    local = _find_peaks(seg)
    if not local:
        return None
    max_peak = max(float(seg[i]) for i in local)
    if not np.isfinite(max_peak) or max_peak <= 0:
        return None
    strong = [i for i in local if seg[i] >= 0.75 * max_peak]
    if not strong:
        return None
    best_lag = min(strong)
    period = best_lag + lag_min
    confidence = float(seg[best_lag])
    # El score prioriza bandas periódicas Y con contraste (las marcas reales),
    # descartando zonas lisas o sin regla.
    score = confidence * energy
    return {"period": period, "confidence": confidence,
            "score": score, "detr": detr}


def _shear_matrix(orientation, sh):
    if orientation == "vertical":
        # y' = sh*x + y  (alinea marcas horizontales inclinadas)
        return np.float32([[1, 0, 0], [sh, 1, 0]])
    # x' = x + sh*y  (alinea marcas verticales inclinadas)
    return np.float32([[1, sh, 0], [0, 1, 0]])


def _band_strip(gray, orientation, sh, start, end):
    """Cizalla la imagen según `sh` y devuelve el perfil 1D de la banda."""
    h, w = gray.shape
    warped = cv2.warpAffine(gray, _shear_matrix(orientation, sh), (w, h),
                            flags=cv2.INTER_LINEAR,
                            borderMode=cv2.BORDER_REPLICATE)
    if orientation == "vertical":
        return warped[:, start:end].mean(axis=1)
    return warped[start:end, :].mean(axis=0)


def _refine_ticks(detr, period):
    """
    A partir del perfil sin tendencia, detecta las posiciones de las marcas
    (mínimos prominentes) y mide la regularidad de su separación.

    Devuelve (tick_positions, spacing, regularity) donde:
      - spacing: mediana de las separaciones consecutivas (sub-píxel, robusta).
      - regularity: 1 - dispersión relativa de las separaciones (0-1); mide
        qué tan parejas están las marcas (confianza intuitiva).
    """
    cand = _find_peaks(-detr)
    if not cand:
        return [], float(period), 0.0
    # Quedarse con los mínimos realmente marcados (oscuros)
    thr = -0.5 * np.std(detr)
    ticks = sorted(c for c in cand if detr[c] < thr)
    if len(ticks) < 3:
        ticks = sorted(cand)
    diffs = np.diff(ticks)
    # Conservar separaciones coherentes con el periodo detectado
    good = diffs[(diffs > 0.6 * period) & (diffs < 1.6 * period)]
    if len(good) >= 2:
        spacing = float(np.median(good))
        rel_disp = float(np.std(good) / np.mean(good)) if np.mean(good) else 1.0
        regularity = max(0.0, 1.0 - rel_disp)
    else:
        spacing = float(period)
        regularity = 0.0
    return ticks, spacing, regularity


def detect_ruler_spacing(image_path, max_dim=1400):
    """
    Detecta automáticamente la separación (en píxeles) entre las marcas de
    una regla, usando la periodicidad de las líneas de la imagen.

    Estrategia:
      1. Reduce la imagen y realza el contraste (CLAHE) para destacar marcas
         tenues.
      2. Busca el ángulo de inclinación (búsqueda gruesa + refinamiento fino)
         probando cizallamientos; el ángulo correcto alinea las marcas y
         maximiza la periodicidad.
      3. Recorre la imagen en BANDAS perpendiculares a las marcas y se queda con
         la de mayor periodicidad y contraste (la zona real de la regla).
      4. Calcula la separación a partir de la mediana de las marcas detectadas
         y una confianza basada en su regularidad.

    Devuelve un diccionario con: ok, error, spacing_px, orientation,
    tick_segments (en coords de la imagen original), confidence, angle_deg.
    """
    gray0 = _imread(image_path, cv2.IMREAD_GRAYSCALE)
    if gray0 is None:
        return {"ok": False, "error": f"No se pudo cargar la imagen: {image_path}"}

    h0, w0 = gray0.shape
    f = min(1.0, max_dim / max(h0, w0))
    if f < 1.0:
        gray = cv2.resize(gray0, (max(int(w0 * f), 1), max(int(h0 * f), 1)),
                          interpolation=cv2.INTER_AREA)
    else:
        gray, f = gray0.copy(), 1.0

    gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray).astype(np.float32)
    h, w = gray.shape

    # --- Búsqueda gruesa de orientación, ángulo y banda ---
    best = None
    for orientation in ("vertical", "horizontal"):
        length, perp = (h, w) if orientation == "vertical" else (w, h)
        band_w = max(30, perp // 20)
        step = max(10, band_w // 2)
        for sh in np.arange(-0.6, 0.601, 0.04):
            warped = cv2.warpAffine(gray, _shear_matrix(orientation, sh),
                                    (w, h), flags=cv2.INTER_LINEAR,
                                    borderMode=cv2.BORDER_REPLICATE)
            for start in range(0, max(1, perp - band_w + 1), step):
                end = min(start + band_w, perp)
                if orientation == "vertical":
                    strip = warped[:, start:end].mean(axis=1)
                else:
                    strip = warped[start:end, :].mean(axis=0)
                res = _analyze_band(strip)
                if res is None:
                    continue
                if best is None or res["score"] > best["score"]:
                    best = {"orientation": orientation, "sh": float(sh),
                            "start": start, "end": end,
                            "score": res["score"], "period": res["period"]}

    if best is None:
        return {"ok": False,
                "error": "No se detectó un patrón periódico de marcas."}

    orientation, b0, b1 = best["orientation"], best["start"], best["end"]

    # --- Refinamiento fino del ángulo en la banda elegida ---
    best_sh, best_res = best["sh"], None
    for sh in np.arange(best["sh"] - 0.04, best["sh"] + 0.0401, 0.008):
        res = _analyze_band(_band_strip(gray, orientation, sh, b0, b1))
        if res is None:
            continue
        if best_res is None or res["score"] > best_res["score"]:
            best_res, best_sh = res, float(sh)

    if best_res is None:
        best_res = _analyze_band(_band_strip(gray, orientation, best_sh, b0, b1))

    detr, period = best_res["detr"], best_res["period"]
    ticks, spacing, regularity = _refine_ticks(detr, period)
    if regularity > 0.9 and period > 0 and abs(spacing - period) / period <= 0.08:
        spacing = float(period)

    # Confianza: la regularidad real de las marcas (más intuitiva) reforzada
    # por la autocorrelación.
    confidence = max(regularity, best_res["confidence"]) if ticks else \
        best_res["confidence"]

    sh = best_sh
    cos_a = 1.0 / np.sqrt(1.0 + sh * sh)
    spacing_real = spacing * cos_a

    # Segmentos en coordenadas de la imagen ORIGINAL (deshace shear y escala)
    segments = []
    for t in ticks:
        if orientation == "vertical":
            segments.append(((b0 / f, (t - sh * b0) / f),
                             (b1 / f, (t - sh * b1) / f)))
        else:
            segments.append((((t - sh * b0) / f, b0 / f),
                             ((t - sh * b1) / f, b1 / f)))

    return {
        "ok": True,
        "error": None,
        "spacing_px": spacing_real / f,
        "orientation": orientation,
        "tick_segments": segments,
        "confidence": float(confidence),
        "angle_deg": float(np.degrees(np.arctan(sh))),
    }


def analyze_image(image_path, darkness_pct=27.0, focus_pct=80.0,
                  um_per_pixel=None,
                  min_area=5, max_area=1000,
                  min_aspect=0.5, max_aspect=5.0,
                  min_circularity=0.8):
    """
    Analiza una imagen y detecta las gotas (círculos negros difusos).

    Parámetros:
        image_path: ruta del archivo de imagen.
        darkness_pct: "Oscuridad" (0-100). Define el umbral de negro;
            valores más altos consideran más píxeles como oscuros.
        focus_pct: "Enfoque" (0-100). Mapea min_core_ratio: la proporción mínima
            de píxeles "core" (bien oscuros/enfocados) dentro del contorno;
            valores más altos exigen gotas más sólidas/nítidas.
        um_per_pixel: micrómetros por píxel (de la calibración). Si es None,
            los tamaños se entregan en píxeles.
        min_area, max_area: filtro de área del contorno (px).
        min_aspect, max_aspect: filtro de relación de aspecto.
        min_circularity: circularidad mínima exigida (1 = círculo perfecto).

    Devuelve un diccionario (ver claves al final de la función).
    """
    image = _imread(image_path)
    if image is None:
        return {"ok": False, "error": f"No se pudo cargar la imagen: {image_path}"}

    # Mapeo de sliders -> parámetros internos
    darkness_pct = max(0.0, min(100.0, darkness_pct))
    focus_pct = max(0.0, min(100.0, focus_pct))
    black_threshold = darkness_pct * 2.55
    # El borde se considera un poco más claro que el núcleo (mismo gap que el
    # script original: 36% - 27% = 9%).
    border_darkness_threshold = min((darkness_pct + 9.0) * 2.55, 255)
    # "Enfoque" controla qué tan sólido/oscuro debe estar el núcleo de la gota.
    min_core_ratio = focus_pct / 100.0

    # Escala de grises + desenfoque para suavizar
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)

    # Umbralización (inversa: lo oscuro queda en blanco)
    _, border_thresh = cv2.threshold(
        blurred, border_darkness_threshold, 255, cv2.THRESH_BINARY_INV)
    _, core_thresh = cv2.threshold(
        blurred, black_threshold, 255, cv2.THRESH_BINARY_INV)

    contours, _ = cv2.findContours(
        border_thresh.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    detected_circles_info = []
    output_image = image.copy()  # imagen con cajas y datos
    debug_image = image.copy()   # imagen con las gotas pintadas

    for contour in contours:
        area = cv2.contourArea(contour)
        x, y, w, h = cv2.boundingRect(contour)

        # 1. Filtro de área
        if not (min_area < area < max_area):
            continue

        # 2. Filtro de relación de aspecto
        aspect_ratio = float(w) / h if h != 0 else 0
        if not (min_aspect < aspect_ratio < max_aspect):
            continue

        # 3. Filtro de circularidad (controlado por "Enfoque")
        perimeter = cv2.arcLength(contour, True)
        if perimeter == 0:
            continue
        circularity = (4 * np.pi * area) / (perimeter * perimeter)
        if circularity < min_circularity:
            continue

        # 4. Chequeo del núcleo (core) con el umbral más estricto
        mask = np.zeros((h, w), dtype=np.uint8)
        contour_roi = contour.copy()
        contour_roi[:, 0, 0] -= x
        contour_roi[:, 0, 1] -= y
        cv2.drawContours(mask, [contour_roi], -1, 255, -1)
        core_roi = core_thresh[y:y + h, x:x + w]
        masked_core_pixels = cv2.bitwise_and(core_roi, mask)
        core_pixel_count = cv2.countNonZero(masked_core_pixels)
        core_ratio = core_pixel_count / area if area != 0 else 0
        if core_ratio < min_core_ratio:
            continue

        detected_circles_info.append({
            "pixel_count": area,
            "max_width": w,
            "max_height": h,
            "bounding_box": (x, y, w, h),
        })

        core = np.logical_and(core_roi == 255, mask == 255)
        debug_roi = debug_image[y:y + h, x:x + w]
        debug_roi[core] = RED_COLOR

        cv2.rectangle(output_image, (x, y), (x + w, y + h), GREEN_COLOR, 2)
        cv2.putText(output_image, f"W: {w}", (x, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, GREEN_COLOR, 2)

    widths_px = [c["max_width"] for c in detected_circles_info]

    # Conversión a micrómetros si hay calibración
    if um_per_pixel:
        widths = [w * um_per_pixel for w in widths_px]
        unit = "\u00b5m"
    else:
        widths = list(widths_px)
        unit = "px"

    mean_width = float(np.mean(widths)) if widths else 0.0
    std_width = float(np.std(widths)) if widths else 0.0

    return {
        "ok": True,
        "error": None,
        "circles": detected_circles_info,
        "widths": widths,
        "widths_px": widths_px,
        "width_counts": Counter(widths_px),
        "unit": unit,
        "mean_width": mean_width,
        "std_width": std_width,
        "count": len(detected_circles_info),
        "total_contours": len(contours),
        "original_rgb": cv2.cvtColor(image, cv2.COLOR_BGR2RGB),
        "output_rgb": cv2.cvtColor(output_image, cv2.COLOR_BGR2RGB),
        "debug_rgb": cv2.cvtColor(debug_image, cv2.COLOR_BGR2RGB),
    }
