"""
Aplicación de escritorio (Tkinter) para la detección de gotas del desalinizador.

Dos pestañas:
  1. Calibración: subir una foto de referencia (regla) y marcar una distancia
     conocida para fijar la escala píxeles -> cm (µm por píxel).
  2. Análisis: subir la foto de gotas, ajustar Oscuridad/Enfoque y ver la
     imagen anotada, el histograma y las estadísticas en µm.

Para generar el ejecutable .exe ver build.bat / README_APP.md.
"""

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import numpy as np
from PIL import Image, ImageTk

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from detector import analyze_image, detect_ruler_spacing


APP_TITLE = "Análisis de tamaño de gota"

# Factores de conversión a micrómetros
UNIT_TO_UM = {"mm": 1000.0, "cm": 10000.0}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1150x760")
        self.minsize(950, 640)

        # Estado de calibración
        self.ref_path = None
        self.ref_image = None          # PIL Image original de referencia
        self.ref_display_scale = 1.0   # escala con que se muestra en el canvas
        self.ref_offset = (0, 0)       # offset (x,y) de la imagen en el canvas
        self.um_per_pixel = None       # resultado de la calibración
        self.ruler = None              # resultado de detect_ruler_spacing

        # Estado de análisis
        self.drops_path = None
        self.result = None
        self._photo_refs = {}

        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        header = ttk.Label(self, text=APP_TITLE, anchor=tk.CENTER,
                           font=("Segoe UI", 16, "bold"), padding=(0, 10))
        header.pack(side=tk.TOP, fill=tk.X)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.tab_calib = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_calib, text="1 · Calibración (referencia)")
        self._build_calib_tab()

        self.tab_analysis = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_analysis, text="2 · Análisis (gráfico)")
        self._build_analysis_tab()

        self.status = ttk.Label(self, text="Listo. Empiece por la pestaña de "
                                "Calibración.", relief=tk.SUNKEN,
                                anchor=tk.W, padding=(8, 4))
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

    # ------------------------------------------------------- pestaña calib
    def _build_calib_tab(self):
        top = ttk.Frame(self.tab_calib, padding=10)
        top.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(top, text="Subir archivo referencia",
                   command=self.open_reference).pack(side=tk.LEFT)

        ttk.Label(top, text="1 división de la regla =").pack(side=tk.LEFT,
                                                             padx=(20, 4))
        self.dist_var = tk.StringVar(value="1")
        ent = ttk.Entry(top, textvariable=self.dist_var, width=8)
        ent.pack(side=tk.LEFT)
        ent.bind("<Return>", lambda e: self.recompute_scale())
        self.unit_var = tk.StringVar(value="mm")
        cb = ttk.Combobox(top, textvariable=self.unit_var, state="readonly",
                          width=5, values=list(UNIT_TO_UM.keys()))
        cb.pack(side=tk.LEFT, padx=4)
        cb.bind("<<ComboboxSelected>>", lambda e: self.recompute_scale())

        ttk.Button(top, text="Detectar de nuevo",
                   command=self.auto_calibrate).pack(side=tk.LEFT, padx=8)

        ttk.Label(self.tab_calib, padding=(10, 0), foreground="#555",
                  text="Suba la foto de la regla: la separación entre marcas se "
                       "detecta automáticamente. Solo indique cuánto vale una "
                       "división y la escala se calcula sola.").pack(
            side=tk.TOP, anchor=tk.W)

        self.calib_canvas = tk.Canvas(self.tab_calib, bg="#222",
                                      highlightthickness=0)
        self.calib_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.calib_canvas.bind("<Configure>", lambda e: self._show_reference())

        self.scale_label = ttk.Label(
            self.tab_calib, text="Escala: sin calibrar (los tamaños se "
            "mostrarán en píxeles).", padding=(10, 6),
            font=("Segoe UI", 10, "bold"))
        self.scale_label.pack(side=tk.BOTTOM, anchor=tk.W)

    def open_reference(self):
        path = filedialog.askopenfilename(
            title="Seleccionar foto de referencia",
            filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff"),
                       ("Todos los archivos", "*.*")])
        if not path:
            return
        try:
            self.ref_image = Image.open(path).convert("RGB")
            self.ref_path = path
            self.status.config(text=f"Referencia cargada: {os.path.basename(path)}. "
                                "Detectando marcas…")
            self._show_reference()
            self.auto_calibrate()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la imagen:\n{e}")

    def auto_calibrate(self):
        """Detecta automáticamente la separación entre marcas y calibra."""
        if not self.ref_path:
            messagebox.showwarning("Calibración",
                                   "Primero suba una foto de referencia.")
            return
        self.ruler = detect_ruler_spacing(self.ref_path)
        if not self.ruler.get("ok"):
            self.um_per_pixel = None
            self.scale_label.config(
                text="No se detectaron marcas automáticamente. Revise que la "
                     "foto muestre la regla con buen contraste.")
            self.status.config(text="Detección automática fallida.")
            self._show_reference()
            return
        self._show_reference()  # redibuja con las marcas detectadas
        self.recompute_scale()

    def recompute_scale(self):
        """Recalcula µm/px a partir de la separación detectada y la división."""
        if not self.ruler or not self.ruler.get("ok"):
            return
        try:
            dist_real = float(self.dist_var.get().replace(",", "."))
            if dist_real <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Calibración",
                                   "Indique un valor de división válido (> 0).")
            return

        spacing_px = self.ruler["spacing_px"]
        dist_um = dist_real * UNIT_TO_UM[self.unit_var.get()]
        self.um_per_pixel = dist_um / spacing_px

        conf = self.ruler.get("confidence", 0) * 100
        self.scale_label.config(
            text=(f"Separación detectada: {spacing_px:.1f} px = {dist_real:g} "
                  f"{self.unit_var.get()}  →  {self.um_per_pixel:.3f} µm/píxel"
                  f"   (confianza {conf:.0f}%)"))
        self.status.config(text="Calibración automática aplicada. Continúe en "
                           "la pestaña de Análisis.")

    def _show_reference(self):
        if self.ref_image is None:
            return
        canvas = self.calib_canvas
        cw, ch = max(canvas.winfo_width(), 1), max(canvas.winfo_height(), 1)
        if cw <= 1 or ch <= 1:
            return
        iw, ih = self.ref_image.size
        scale = min(cw / iw, ch / ih)
        self.ref_display_scale = scale
        new_size = (max(int(iw * scale), 1), max(int(ih * scale), 1))
        off_x = (cw - new_size[0]) // 2
        off_y = (ch - new_size[1]) // 2
        self.ref_offset = (off_x, off_y)

        disp = self.ref_image.resize(new_size, Image.LANCZOS)
        photo = ImageTk.PhotoImage(disp)
        self._photo_refs["ref"] = photo
        canvas.delete("all")
        canvas.create_image(off_x, off_y, image=photo, anchor=tk.NW)
        self._draw_detected_marks()

    def _draw_detected_marks(self):
        """Dibuja las marcas detectadas automáticamente (siguiendo la
        inclinación) sobre la banda donde se encontró la regla."""
        if not self.ruler or not self.ruler.get("ok"):
            return
        canvas = self.calib_canvas
        canvas.delete("mark")
        sc = self.ref_display_scale
        ox, oy = self.ref_offset
        for (p0, p1) in self.ruler.get("tick_segments", []):
            canvas.create_line(ox + p0[0] * sc, oy + p0[1] * sc,
                               ox + p1[0] * sc, oy + p1[1] * sc,
                               fill="#2a7ae2", width=1, tags="mark")

    # ---------------------------------------------------- pestaña análisis
    def _build_analysis_tab(self):
        top = ttk.Frame(self.tab_analysis, padding=10)
        top.pack(side=tk.TOP, fill=tk.X)
        ttk.Button(top, text="Cargar archivo de gotas",
                   command=self.open_drops).pack(side=tk.LEFT)
        self.drops_label = ttk.Label(top, text="Ninguna foto de gotas cargada.",
                                     foreground="#666")
        self.drops_label.pack(side=tk.LEFT, padx=10)

        body = ttk.Frame(self.tab_analysis)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Izquierda: imagen + sliders
        left = ttk.Frame(body)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.drops_canvas = tk.Canvas(left, bg="#000", highlightthickness=0)
        self.drops_canvas.pack(fill=tk.BOTH, expand=True)
        self.drops_canvas.bind("<Configure>", lambda e: self._refresh_drops_image())

        sliders = ttk.Frame(left, padding=(0, 8))
        sliders.pack(side=tk.BOTTOM, fill=tk.X)

        ttk.Label(sliders, text="Oscuridad").grid(row=0, column=0, sticky=tk.W)
        self.darkness_var = tk.DoubleVar(value=27.0)
        self.darkness_scale = ttk.Scale(
            sliders, from_=0, to=100, variable=self.darkness_var,
            command=lambda e: self._on_slider_change("darkness"))
        self.darkness_scale.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        self.darkness_lbl = ttk.Label(sliders, text="27%", width=6)
        self.darkness_lbl.grid(row=1, column=1)

        ttk.Label(sliders, text="Enfoque").grid(row=2, column=0, sticky=tk.W)
        self.focus_var = tk.DoubleVar(value=80.0)
        self.focus_scale = ttk.Scale(
            sliders, from_=0, to=100, variable=self.focus_var,
            command=lambda e: self._on_slider_change("focus"))
        self.focus_scale.grid(row=3, column=0, sticky="ew", padx=(0, 10))
        self.focus_lbl = ttk.Label(sliders, text="80%", width=6)
        self.focus_lbl.grid(row=3, column=1)
        sliders.columnconfigure(0, weight=1)

        # Derecha: histograma + estadísticas
        right = ttk.Frame(body)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self._reset_axes()
        self.chart_canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.chart_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.chart_canvas.draw()

        self.stats_label = ttk.Label(
            right, text="Gotas reconocidas: –\nTamaño promedio: –\n"
            "Desviación estándar: –", font=("Segoe UI", 11), padding=(0, 8))
        self.stats_label.pack(side=tk.BOTTOM, anchor=tk.W)

    def _reset_axes(self):
        self.ax.clear()
        self.ax.set_title("Distribución de tamaños")
        self.ax.set_xlabel("Tamaño")
        self.ax.set_ylabel("Frecuencia")

    def open_drops(self):
        path = filedialog.askopenfilename(
            title="Seleccionar foto de gotas",
            filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff"),
                       ("Todos los archivos", "*.*")])
        if not path:
            return
        self.drops_path = path
        self.drops_label.config(text=os.path.basename(path), foreground="#000")
        if self.um_per_pixel is None:
            messagebox.showinfo(
                "Sin calibración",
                "No hay calibración: los tamaños se mostrarán en píxeles.\n"
                "Para obtener µm, calibre primero en la pestaña 1.")
        self._run_analysis()

    def _on_slider_change(self, which):
        self.darkness_lbl.config(text=f"{self.darkness_var.get():.0f}%")
        self.focus_lbl.config(text=f"{self.focus_var.get():.0f}%")
        # Re-analizar al soltar el slider (con debounce simple)
        if self.drops_path:
            if hasattr(self, "_slider_job"):
                self.after_cancel(self._slider_job)
            self._slider_job = self.after(300, self._run_analysis)

    def _run_analysis(self):
        if not self.drops_path:
            return
        self.status.config(text="Analizando…")
        darkness = self.darkness_var.get()
        focus = self.focus_var.get()
        upp = self.um_per_pixel
        path = self.drops_path

        def worker():
            res = analyze_image(path, darkness_pct=darkness, focus_pct=focus,
                                um_per_pixel=upp)
            self.after(0, lambda: self._on_analysis_done(res))

        threading.Thread(target=worker, daemon=True).start()

    def _on_analysis_done(self, res):
        if not res.get("ok"):
            messagebox.showerror("Error", res.get("error", "Error desconocido"))
            self.status.config(text="Error en el análisis.")
            return
        self.result = res
        self._refresh_drops_image()
        self._refresh_chart()

        unit = res["unit"]
        self.stats_label.config(text=(
            f"Gotas reconocidas: {res['count']}\n"
            f"Tamaño promedio: {res['mean_width']:.1f} {unit}\n"
            f"Desviación estándar: {res['std_width']:.1f} {unit}"))
        self.status.config(text=(
            f"Análisis listo. {res['count']} gotas "
            f"(de {res['total_contours']} contornos iniciales)."))

    def _refresh_drops_image(self):
        if not self.result:
            return
        arr = self.result.get("output_rgb")
        if arr is None:
            return
        canvas = self.drops_canvas
        cw, ch = max(canvas.winfo_width(), 1), max(canvas.winfo_height(), 1)
        if cw <= 1 or ch <= 1:
            return
        img = Image.fromarray(arr)
        iw, ih = img.size
        scale = min(cw / iw, ch / ih)
        new_size = (max(int(iw * scale), 1), max(int(ih * scale), 1))
        img = img.resize(new_size, Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        self._photo_refs["drops"] = photo
        canvas.delete("all")
        canvas.create_image(cw // 2, ch // 2, image=photo, anchor=tk.CENTER)

    def _refresh_chart(self):
        self._reset_axes()
        widths = self.result.get("widths", [])
        unit = self.result.get("unit", "px")
        if widths:
            self.ax.hist(widths, bins=30, color="#2a7ae2", edgecolor="white")
            mean = self.result["mean_width"]
            self.ax.axvline(mean, color="red", linestyle="--", linewidth=1.5,
                            label=f"Media = {mean:.1f} {unit}")
            self.ax.legend()
            self.ax.set_xlabel(f"Tamaño ({unit})")
        else:
            self.ax.text(0.5, 0.5, "Sin gotas detectadas", ha="center",
                         va="center", transform=self.ax.transAxes,
                         color="#999", fontsize=14)
        self.fig.tight_layout()
        self.chart_canvas.draw()


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
