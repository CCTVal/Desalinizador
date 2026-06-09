"""
QA detallado del backend (detector.py).
Genera imágenes con verdad-conocida y valida con asserts. Imprime PASS/FAIL.
"""
import os, tempfile, traceback
import numpy as np
import cv2
from detector import detect_ruler_spacing, analyze_image

UNIT_TO_UM = {"mm": 1000.0, "cm": 10000.0}
TMP = tempfile.mkdtemp(prefix="qa_")
P = F = 0
fails = []


def check(name, cond, detail=""):
    global P, F
    if cond:
        P += 1
        print(f"  PASS  {name}  {detail}")
    else:
        F += 1
        fails.append(name)
        print(f"  FAIL  {name}  {detail}")


def make_ruler(spacing, angle=0, bright=1.0, w=900, h=1200, noise=0,
               tick_len=120, major_every=10):
    img = np.full((h, w, 3), 245, np.uint8)
    cx = w // 2
    for i, y in enumerate(range(0, h, spacing)):
        L = tick_len + (60 if i % major_every == 0 else 0)
        cv2.line(img, (cx, y), (cx + L, y), (20, 20, 20), 2)
    cv2.line(img, (cx, 0), (cx, h), (60, 60, 60), 2)  # borde
    if angle:
        M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        img = cv2.warpAffine(img, M, (w, h), borderValue=(245, 245, 245))
    if bright != 1.0:
        img = (img.astype(np.float32) * bright).astype(np.uint8)
    if noise:
        img = np.clip(img.astype(np.int16) +
                      np.random.randint(-noise, noise + 1, img.shape), 0, 255
                      ).astype(np.uint8)
    path = os.path.join(TMP, f"r_{spacing}_{angle}_{int(bright*100)}_{noise}.jpg")
    cv2.imwrite(path, img)
    return path


def make_drops(diams, upp_w=700, upp_h=500):
    img = np.full((upp_h, upp_w, 3), 235, np.uint8)
    n = len(diams)
    for i, d in enumerate(diams):
        cx = int((i + 1) * upp_w / (n + 1))
        cv2.circle(img, (cx, upp_h // 2), max(1, d // 2), (5, 5, 5), -1)
    path = os.path.join(TMP, "drops_" + "_".join(map(str, diams)) + ".jpg")
    cv2.imwrite(path, img)
    return path


print("\n### A) PRECISION DE SEPARACION (sin inclinacion) ###")
for sp in (20, 40, 60, 100, 150):
    r = detect_ruler_spacing(make_ruler(sp))
    err = abs(r["spacing_px"] - sp) / sp * 100
    check(f"spacing={sp}px", r["ok"] and err < 4,
          f"detectado={r['spacing_px']:.1f} err={err:.1f}% conf={r['confidence']:.2f}")

print("\n### B) PRECISION CON INCLINACION (spacing real=60) ###")
for ang in (-30, -20, -10, -5, 5, 10, 20, 30):
    r = detect_ruler_spacing(make_ruler(60, angle=ang))
    err = abs(r["spacing_px"] - 60) / 60 * 100
    angerr = abs(abs(r["angle_deg"]) - abs(ang))
    check(f"angulo={ang}", r["ok"] and err < 6 and angerr < 4,
          f"spacing={r['spacing_px']:.1f}(err{err:.0f}%) ang={r['angle_deg']:.1f} conf={r['confidence']:.2f}")

print("\n### C) IMAGENES OSCURAS (spacing=60, ang=10) ###")
for b in (0.5, 0.3, 0.18, 0.1):
    r = detect_ruler_spacing(make_ruler(60, angle=10, bright=b))
    err = abs(r["spacing_px"] - 60) / 60 * 100
    check(f"brillo={b}", r["ok"] and err < 6,
          f"spacing={r['spacing_px']:.1f} err={err:.0f}% conf={r['confidence']:.2f}")

print("\n### D) CON RUIDO (spacing=60) ###")
for nz in (10, 25, 40):
    r = detect_ruler_spacing(make_ruler(60, angle=8, noise=nz))
    err = abs(r["spacing_px"] - 60) / 60 * 100
    check(f"ruido=+-{nz}", r["ok"] and err < 8,
          f"spacing={r['spacing_px']:.1f} err={err:.0f}% conf={r['confidence']:.2f}")

print("\n### E) ORIENTACION HORIZONTAL (regla acostada) ###")
img = np.full((700, 1100, 3), 245, np.uint8)
for x in range(0, 1100, 55):
    cv2.line(img, (x, 300), (x, 420), (20, 20, 20), 2)
hp = os.path.join(TMP, "horiz.jpg"); cv2.imwrite(hp, img)
r = detect_ruler_spacing(hp)
check("horizontal spacing=55", r["ok"] and abs(r["spacing_px"] - 55) / 55 < 0.05,
      f"orient={r['orientation']} spacing={r['spacing_px']:.1f} conf={r['confidence']:.2f}")

print("\n### F) CASOS LIMITE / ERRORES ###")
r = detect_ruler_spacing("NO_EXISTE_xyz.jpg")
check("archivo inexistente -> ok=False", r["ok"] is False, r.get("error", "")[:30])
blank = os.path.join(TMP, "blank.jpg"); cv2.imwrite(blank, np.full((400, 400, 3), 200, np.uint8))
r = detect_ruler_spacing(blank)
check("imagen en blanco -> ok=False o conf baja",
      (r["ok"] is False) or (r.get("confidence", 1) < 0.5),
      f"ok={r['ok']} conf={r.get('confidence')}")
np.random.seed(0)
noiseimg = os.path.join(TMP, "noise.jpg")
cv2.imwrite(noiseimg, np.random.randint(0, 255, (500, 500, 3), np.uint8))
r = detect_ruler_spacing(noiseimg)
check("ruido puro -> conf baja (<0.6)", (not r["ok"]) or r["confidence"] < 0.6,
      f"ok={r['ok']} conf={r.get('confidence')}")

print("\n### G) DETECCION DE GOTAS: conteo y conversion ###")
upp = 1000.0 / 60  # 1mm=60px -> 16.667 um/px
res = analyze_image(make_drops([10, 16, 22, 28, 34]), darkness_pct=40,
                    focus_pct=50, um_per_pixel=upp)
check("cuenta 5 gotas (todas <max_area)", res["count"] == 5,
      f"count={res['count']} widths_px={sorted(res['widths_px'])}")
conv_ok = all(abs(w_um - w_px * upp) < 0.01
              for w_px, w_um in zip(res["widths_px"], res["widths"]))
check("conversion px->um exacta", conv_ok)
check("unidad = um con calibracion", res["unit"] == "µm", res["unit"])
check("media/std correctas",
      abs(res["mean_width"] - np.mean(res["widths"])) < 0.01 and
      abs(res["std_width"] - np.std(res["widths"])) < 0.01,
      f"media={res['mean_width']:.1f} std={res['std_width']:.1f}")

print("\n### H) SIN CALIBRACION -> unidad px ###")
res = analyze_image(make_drops([20, 24]), darkness_pct=40, focus_pct=50)
check("unidad = px sin calibracion", res["unit"] == "px", res["unit"])
check("widths == widths_px sin calib", res["widths"] == res["widths_px"])

print("\n### I) FILTRO max_area (gota grande se descarta) ###")
res = analyze_image(make_drops([20, 50]), darkness_pct=40, focus_pct=50)
check("gota d=50 (area>1000) descartada", res["count"] == 1,
      f"count={res['count']} (esperado 1)")

print("\n### J) FILTRO min_area (ruido pequeno se descarta) ###")
res = analyze_image(make_drops([2, 20]), darkness_pct=40, focus_pct=50)
check("punto d=2 (area<min) descartado", res["count"] == 1,
      f"count={res['count']} (esperado 1)")

print("\n### K) MAPEO 'Oscuridad' (umbral) ###")
dp = make_drops([20, 24, 28])
c_lo = analyze_image(dp, darkness_pct=2, focus_pct=50)["count"]
c_hi = analyze_image(dp, darkness_pct=40, focus_pct=50)["count"]
check("darkness muy bajo detecta menos que alto", c_lo <= c_hi,
      f"d=2%->{c_lo}  d=40%->{c_hi}")

print("\n### L) MAPEO 'Enfoque' (min_core_ratio) ###")
# gota con nucleo hueco (anillo) -> con enfoque alto debe descartarse
img = np.full((400, 400, 3), 235, np.uint8)
cv2.circle(img, (200, 200), 14, (5, 5, 5), 3)   # anillo (no solido)
ring = os.path.join(TMP, "ring.jpg"); cv2.imwrite(ring, img)
c_low_focus = analyze_image(ring, darkness_pct=40, focus_pct=20)["count"]
c_high_focus = analyze_image(ring, darkness_pct=40, focus_pct=95)["count"]
check("enfoque alto exige nucleo solido", c_high_focus <= c_low_focus,
      f"foco20%->{c_low_focus}  foco95%->{c_high_focus}")

print("\n### M) ERRORES analyze_image ###")
res = analyze_image("NO_EXISTE.jpg")
check("analyze archivo inexistente -> ok=False", res["ok"] is False)

print("\n### N) IMAGEN SIN GOTAS -> count 0, media 0 ###")
empty = os.path.join(TMP, "empty.jpg"); cv2.imwrite(empty, np.full((300, 300, 3), 235, np.uint8))
res = analyze_image(empty, darkness_pct=40, focus_pct=50)
check("sin gotas count=0", res["ok"] and res["count"] == 0,
      f"count={res['count']} media={res['mean_width']}")

print("\n" + "=" * 55)
print(f"RESULTADO: {P} PASS, {F} FAIL")
if fails:
    print("FALLOS:", ", ".join(fails))
print("=" * 55)
