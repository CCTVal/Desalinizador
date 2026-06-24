"""
QA del front-end (app.py). Construye la App y valida la interfaz de forma
programatica (sin interaccion manual). Imprime PASS/FAIL como qa_test.py.

Ejecutar:  python qa_front.py
"""
import time
import tkinter as tk

from PIL import ImageTk

import app
from detector import detect_ruler_spacing

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


def pump(a, secs=1.0, until=None):
    """Bombea el loop de Tk hasta `secs` o hasta que `until()` sea verdadero."""
    t0 = time.time()
    while time.time() - t0 < secs:
        a.update()
        time.sleep(0.02)
        if until and until():
            break


a = app.App()
a.geometry("1300x860")
a.update()

print("\n### A) ARRANQUE Y PANTALLA INICIAL ###")
check("App construye y es Tk", hasattr(a, "mainloop"))
check("inicia en calibracion (2 tarjetas)", len(a._cards) == 2,
      f"cards={len(a._cards)}")
check("logo/brand cargado", a._brand is not None)

print("\n### B) RECURSOS GRAFICOS ###")
g = app._make_gradient(400, 300)
check("gradiente generado", g.size == (400, 300) and g.mode == "RGB")
cardimg = app._make_card(300, 200)
check("tarjeta PIL con sombra (RGBA)",
      cardimg.mode == "RGBA" and cardimg.size == (360, 260),
      f"size={cardimg.size}")
check("_tint aclara el color", app._tint("#2e31c6", 0.74) != "#2e31c6",
      app._tint("#2e31c6", 0.74))

print("\n### C) ICONOS ###")
ok_icons = True
for fn in (app.upload_badge, app.gear_icon, app.doc_icon,
           lambda p: app.check_badge(p)):
    try:
        fn(a)
    except Exception as exc:           # noqa: BLE001
        ok_icons = False
        print("   error icono:", exc)
check("iconos se dibujan sin error", ok_icons)

print("\n### D) SLIDER (mapeo de %) ###")
v = tk.DoubleVar(value=0)
s = app.Slider(a, v)
a.update()
s.var.set(52)
s._draw()
check("slider refleja el valor", abs(s.var.get() - 52) < 1e-6)
x0, x1 = s._ends(s._width())
check("slider tiene cápsula con extremos", x1 > x0)

print("\n### E) BOTONES (estilos con color) ###")
st = app.RoundButton._STYLES
check("primary indigo", st["primary"]["fill"] == app.PRIMARY,
      st["primary"]["fill"])
check("ghost texto/borde azul", st["ghost"]["fg"] == app.ACCENT,
      st["ghost"]["fg"])
check("light fondo azul claro", st["light"]["fill"] == "#e7ecfb",
      st["light"]["fill"])

print("\n### F) PANTALLA DE CARGA + ASYNC (hilo) ###")
done = {}
a._run_async(lambda: (time.sleep(0.4) or 99), lambda r: done.__setitem__("r", r),
             "QA en proceso…")
check("overlay visible al iniciar", a._loading is not None)
pump(a, 3.0, until=lambda: "r" in done)
check("callback recibe el resultado", done.get("r") == 99)
check("overlay oculto al terminar", a._loading is None)

print("\n### G) CALIBRACION: deteccion + preview de marcas ###")
a.calib_path = "test_ruler_real.jpg"
a.ruler = detect_ruler_spacing("test_ruler_real.jpg")
check("regla detectada", a.ruler.get("ok"),
      f"spacing={a.ruler.get('spacing_px',0):.1f} conf={a.ruler.get('confidence',0):.2f}")
prev = a._ruler_preview()
check("preview de regla es PhotoImage con marcas",
      isinstance(prev, ImageTk.PhotoImage) and prev.width() > 0,
      f"marcas={len(a.ruler.get('tick_segments', []))}")

print("\n### H) ANALISIS DE GOTAS -> PANTALLA DE RESULTADOS ###")
a.um_per_pixel = None
a.drops_path = "test_synth.jpg"
a._submit_drops()
pump(a, 4.0, until=lambda: a.result is not None and a._loading is None)
check("result poblado (ok)", bool(a.result and a.result.get("ok")),
      f"count={a.result.get('count') if a.result else None}")
check("pantalla resultados (canvas + chart)",
      hasattr(a, "drops_canvas") and hasattr(a, "chart_canvas"))
check("estadisticas renderizadas", len(a.stats_box.winfo_children()) > 0)

print("\n### I) ZOOM ###")
check("zoom inicial 100%", a.zoom_lbl.cget("text") == "100%")
a._zoom_by(1.25)
a._zoom_by(1.25)
a.update()
check("zoom + aumenta y actualiza etiqueta",
      a.drops_zoom > 1.0 and a.zoom_lbl.cget("text") != "100%",
      f"zoom={a.drops_zoom:.2f} lbl={a.zoom_lbl.cget('text')}")
a._reset_zoom()
a.update()
check("ajustar vuelve a 100%", a.zoom_lbl.cget("text") == "100%")

print("\n### J) NAVEGACION ENTRE PANTALLAS ###")
a.show_calibration()
a.update()
check("vuelve a calibracion (2 tarjetas)", len(a._cards) == 2)
a.show_drops()
a.update()
check("pantalla de gotas (1 tarjeta)", len(a._cards) == 1)

a.destroy()

print("\n" + "=" * 55)
print(f"RESULTADO FRONT-END: {P} PASS, {F} FAIL")
if fails:
    print("FALLOS:", ", ".join(fails))
print("=" * 55)
