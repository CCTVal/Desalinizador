"""
Agente de pruebas de la aplicacion COMPLETA.

Corre, en una sola ejecucion, todas las suites y entrega un reporte unificado:
  1. BACKEND      -> qa_test.py   (deteccion de regla y gotas)
  2. FRONT-END    -> qa_front.py  (UI: pantallas, carga, zoom, etc.)
  3. INTEGRACION  -> flujo real E2E (calibracion -> gotas -> resultados -> zoom)

Devuelve exit code 0 si todo pasa, 1 si hay algun FAIL (para usar en build/CI).

Ejecutar:  python qa_all.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# La consola de Windows (cp1252) no puede imprimir 'µm'; forzamos UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Entorno para que los subprocesos emitan UTF-8 (no cp1252).
_ENV = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")


def run_script(label, script):
    """Corre una suite como subproceso aislado y devuelve (pass, fail)."""
    print("\n" + "#" * 62)
    print(f"# {label}")
    print("#" * 62)
    proc = subprocess.run(
        [sys.executable, os.path.join(HERE, script)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=_ENV)
    print(proc.stdout, end="")
    if proc.returncode != 0 and proc.stderr:
        print(proc.stderr, end="")
    m = re.search(r"(\d+)\s+PASS,\s+(\d+)\s+FAIL", proc.stdout or "")
    if not m:
        print(f"  (no se pudo leer el resumen de {script})")
        return 0, 1
    return int(m.group(1)), int(m.group(2))


def run_integration():
    """Flujo real de punta a punta usando las imagenes de prueba y la UI."""
    import time as _t
    import app
    from detector import detect_ruler_spacing

    print("\n" + "#" * 62)
    print("# INTEGRACION E2E (flujo real con imagenes de prueba)")
    print("#" * 62)
    P = F = 0

    def chk(name, cond, detail=""):
        nonlocal P, F
        if cond:
            P += 1
            print(f"  PASS  {name}  {detail}")
        else:
            F += 1
            print(f"  FAIL  {name}  {detail}")

    a = app.App()
    a.geometry("1300x860")
    a.update()

    # 1) Calibracion real con la foto de la regla
    a.calib_path = "test_ruler_real.jpg"
    a.ruler = detect_ruler_spacing("test_ruler_real.jpg")
    chk("1. regla detectada", a.ruler.get("ok"),
        f"spacing={a.ruler.get('spacing_px', 0):.1f}px "
        f"conf={a.ruler.get('confidence', 0):.2f}")
    sp = a.ruler.get("spacing_px", 0) or 1.0
    a.um_per_pixel = 1.0 * 1000.0 / sp          # 1 division = 1 mm
    chk("2. um/pixel calculado", a.um_per_pixel > 0,
        f"{a.um_per_pixel:.2f} um/px")
    chk("3. preview de la regla con marcas", a._ruler_preview() is not None)

    # 2) Analisis de gotas con la pantalla de carga (flujo async real)
    a.drops_path = "test_synth.jpg"
    a._submit_drops()
    chk("4. overlay de carga aparece", a._loading is not None)
    t0 = _t.time()
    while _t.time() - t0 < 5:
        a.update()
        _t.sleep(0.02)
        if a.result is not None and a._loading is None:
            break
    chk("5. analisis completado", bool(a.result and a.result.get("ok")),
        f"count={a.result.get('count') if a.result else None}")
    chk("6. tamanos en um (calibrado)", a.result.get("unit") == "µm",
        a.result.get("unit"))
    chk("7. pantalla de resultados lista",
        hasattr(a, "drops_canvas") and len(a.stats_box.winfo_children()) > 0)

    # 3) Zoom: acercar y volver a ajustar
    a._zoom_by(1.25)
    a.update()
    zmax = a.zoom_lbl.cget("text")
    a._reset_zoom()
    a.update()
    chk("8. zoom + y ajustar", zmax != "100%" and
        a.zoom_lbl.cget("text") == "100%", f"zoom_max={zmax}")

    # 4) Cargar nuevo archivo -> vuelve a la pantalla de gotas
    a.show_drops()
    a.update()
    chk("9. 'cargar nuevo archivo' vuelve a gotas", len(a._cards) == 1)

    a.destroy()
    return P, F


def main():
    rows = []
    total_p = total_f = 0

    for label, script in (("BACKEND   (qa_test.py)", "qa_test.py"),
                          ("FRONT-END (qa_front.py)", "qa_front.py")):
        p, f = run_script(label, script)
        rows.append((label, p, f))
        total_p += p
        total_f += f

    p, f = run_integration()
    rows.append(("INTEGRACION E2E", p, f))
    total_p += p
    total_f += f

    print("\n" + "=" * 62)
    print("  RESUMEN DE LA APLICACION COMPLETA")
    print("=" * 62)
    for label, p, f in rows:
        estado = "OK   " if f == 0 else "FALLA"
        print(f"  [{estado}] {label:30s} {p:3d} PASS   {f:2d} FAIL")
    print("-" * 62)
    print(f"  TOTAL: {total_p} PASS, {total_f} FAIL")
    print("=" * 62)
    sys.exit(0 if total_f == 0 else 1)


if __name__ == "__main__":
    main()
