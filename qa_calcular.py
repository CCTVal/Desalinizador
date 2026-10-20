"""Prueba del botón Calcular: los sliders no recalculan solos, Calcular aplica
los valores y la navegación usa los valores aplicados (no los pendientes)."""

import gc
import os
import tempfile
import time
from types import SimpleNamespace
from unittest import mock

import cv2
import numpy as np

import app


def make_image(path, centers):
    image = np.full((100, 200, 3), 235, dtype=np.uint8)
    for center in centers:
        cv2.circle(image, (center, 50), 10, (5, 5, 5), -1)
    assert cv2.imwrite(path, image)


def pump(window, predicate, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        window.update()
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("La interfaz no completó el análisis a tiempo")


def label_texts(widget):
    """Textos de todas las etiquetas dentro de un contenedor (recursivo)."""
    texts = []
    for child in widget.winfo_children():
        if isinstance(child, app.tk.Label):
            texts.append(child.cget("text"))
        texts.extend(label_texts(child))
    return texts


def main():
    with tempfile.TemporaryDirectory(dir=os.path.dirname(__file__)) as directory:
        first = os.path.join(directory, "foto_1.png")
        second = os.path.join(directory, "foto_2.png")
        make_image(first, [50])
        make_image(second, [50, 140])

        window = app.App()
        try:
            window.geometry("1300x790")
            window.update()
            window.um_per_pixel = 2.0
            window.show_drops()
            window.drops_zone._on_drop(
                SimpleNamespace(data=f"{{{first}}} {{{second}}}"))
            with mock.patch.object(app.messagebox, "showerror"), \
                    mock.patch.object(app.messagebox, "showwarning"):
                window._submit_drops()
                pump(window, lambda: window._screen == "results" and
                     window._loading is None)

                # 1) Mover sliders NO dispara análisis.
                jobs_before = window._job_seq
                applied_before = (window.applied_darkness, window.applied_focus)
                window.darkness_var.set(10)
                window.focus_var.set(30)
                window.update()
                assert window._job_seq == jobs_before, \
                    "Mover un slider lanzó un análisis"
                assert (window.applied_darkness, window.applied_focus) == applied_before

                # 2) Navegar usa los valores aplicados, no los pendientes.
                seen = {}
                real_analyze = app._analyze_image

                def spy(path, darkness_pct, focus_pct, um_per_pixel):
                    seen["darkness"], seen["focus"] = darkness_pct, focus_pct
                    return real_analyze(path, darkness_pct=darkness_pct,
                                        focus_pct=focus_pct,
                                        um_per_pixel=um_per_pixel)

                with mock.patch.object(app, "_analyze_image", side_effect=spy):
                    window._select_result(1)
                    pump(window, lambda: window.drops_path == second and
                         window._loading is None)
                assert seen["darkness"] == applied_before[0], seen
                assert seen["focus"] == applied_before[1], seen

                # 3) Calcular aplica los valores de los sliders.
                window.darkness_var.set(10)
                window.focus_var.set(30)
                window._recalculate()
                pump(window, lambda: window._loading is None)
                assert window.applied_darkness == 10
                assert window.applied_focus == 30
                assert window.batch_results[first]["count"] == 1
                assert window.batch_results[second]["count"] == 2

                # 4) La línea de lote muestra los totales globales.
                texts = " ".join(label_texts(window.stats_box))
                assert "2/2 fotos" in texts, texts
                assert "3 gotas" in texts, texts
                assert "promedio" in texts and "desviación" in texts, texts

                # 5) Un recálculo fallido no cambia valores ni resultados.
                good_counts = (window.batch_results[first]["count"],
                               window.batch_results[second]["count"])
                window.darkness_var.set(60)
                failed = {"summaries": {}, "errors": {first: "fallo"},
                          "display_path": None, "display_result": None}
                with mock.patch.object(app, "_analyze_batch",
                                       return_value=failed):
                    window._recalculate()
                    pump(window, lambda: window._loading is None)
                assert (window.applied_darkness, window.applied_focus) == (10, 30), \
                    "Un recálculo fallido cambió los valores aplicados"
                assert (window.batch_results[first]["count"],
                        window.batch_results[second]["count"]) == good_counts

            window.show_drops()
            window._clear_drops_file()
            assert not window.drops_paths
        finally:
            window.destroy()
            gc.collect()
    print("PASS: sliders sin recálculo, Calcular aplica valores, navegación y totales")


if __name__ == "__main__":
    main()
