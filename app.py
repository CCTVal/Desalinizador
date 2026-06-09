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

from PIL import Image, ImageTk

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from detector import analyze_image, detect_ruler_spacing


APP_TITLE = "Análisis de tamaño de gota"

# Factores de conversión a micrómetros
UNIT_TO_UM = {"mm": 1000.0, "cm": 10000.0}

# Opacidad de la pantalla de carga (0 = invisible, 1 = opaca)
LOADING_ALPHA = 0.55


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

        # Zoom/desplazamiento de la imagen de gotas
        self.drops_zoom = 1.0          # 1.0 = ajustada a la ventana
        self.drops_pan = [0.0, 0.0]    # desplazamiento en píxeles del canvas
        self._pan_anchor = None

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

        self.calib_hint = ttk.Label(
            self.tab_calib, padding=(10, 0), foreground="#555",
            text="Suba la foto de la regla: la separación entre marcas se "
                 "detecta automáticamente. Solo indique cuánto vale una "
                 "división y la escala se calcula sola.")
        self.calib_hint.pack(side=tk.TOP, anchor=tk.W)

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
            self._show_reference()
            self.status.config(text=f"Referencia cargada: "
                               f"{os.path.basename(path)}. Detectando marcas…")
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

        # Barra de botones de zoom
        zoombar = ttk.Frame(left, padding=(0, 4))
        zoombar.pack(side=tk.TOP, fill=tk.X)
        ttk.Button(zoombar, text="Zoom +", width=8,
                   command=lambda: self._zoom_by(1.25)).pack(side=tk.LEFT)
        ttk.Button(zoombar, text="Zoom −", width=8,
                   command=lambda: self._zoom_by(1 / 1.25)).pack(side=tk.LEFT,
                                                                 padx=4)
        ttk.Button(zoombar, text="Ajustar", width=8,
                   command=self._reset_zoom).pack(side=tk.LEFT)
        self.zoom_lbl = ttk.Label(zoombar, text="100%", width=6,
                                  foreground="#666")
        self.zoom_lbl.pack(side=tk.LEFT, padx=8)
        ttk.Label(zoombar, foreground="#888",
                  text="Rueda: zoom · Arrastrar: mover · Doble clic: ajustar"
                  ).pack(side=tk.LEFT, padx=4)

        self.drops_canvas = tk.Canvas(left, bg="#000", highlightthickness=0)
        self.drops_canvas.pack(fill=tk.BOTH, expand=True)
        self.drops_canvas.bind("<Configure>", lambda e: self._refresh_drops_image())
        # Zoom con la rueda, arrastrar para mover, doble clic para resetear
        self.drops_canvas.bind("<MouseWheel>", self._on_zoom)        # Windows
        self.drops_canvas.bind("<Button-4>", self._on_zoom)          # Linux up
        self.drops_canvas.bind("<Button-5>", self._on_zoom)          # Linux down
        self.drops_canvas.bind("<ButtonPress-1>", self._on_pan_start)
        self.drops_canvas.bind("<B1-Motion>", self._on_pan_move)
        self.drops_canvas.bind("<Double-Button-1>", lambda e: self._reset_zoom())

        sliders = ttk.Frame(left, padding=(0, 8))
        sliders.pack(side=tk.BOTTOM, fill=tk.X)

        ttk.Label(sliders, text="Oscuridad").grid(row=0, column=0, sticky=tk.W)
        self.darkness_var = tk.DoubleVar(value=27.0)
        self.darkness_scale = ttk.Scale(
            sliders, from_=0, to=100, variable=self.darkness_var,
            command=lambda e: self._update_slider_labels())
        self.darkness_scale.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        self.darkness_lbl = ttk.Label(sliders, text="27%", width=6)
        self.darkness_lbl.grid(row=1, column=1)

        ttk.Label(sliders, text="Enfoque").grid(row=2, column=0, sticky=tk.W)
        self.focus_var = tk.DoubleVar(value=80.0)
        self.focus_scale = ttk.Scale(
            sliders, from_=0, to=100, variable=self.focus_var,
            command=lambda e: self._update_slider_labels())
        self.focus_scale.grid(row=3, column=0, sticky="ew", padx=(0, 10))
        self.focus_lbl = ttk.Label(sliders, text="80%", width=6)
        self.focus_lbl.grid(row=3, column=1)
        sliders.columnconfigure(0, weight=1)

        # Analizar SOLO al soltar el slider (no en cada porcentaje intermedio)
        self.darkness_scale.bind("<ButtonRelease-1>",
                                 lambda e: self._on_slider_release())
        self.focus_scale.bind("<ButtonRelease-1>",
                              lambda e: self._on_slider_release())

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
        self.drops_zoom = 1.0
        self.drops_pan = [0.0, 0.0]
        if self.um_per_pixel is None:
            messagebox.showinfo(
                "Sin calibración",
                "No hay calibración: los tamaños se mostrarán en píxeles.\n"
                "Para obtener µm, calibre primero en la pestaña 1.")
        self._run_analysis()

    def _update_slider_labels(self):
        """Actualiza el % en vivo mientras se arrastra (sin analizar)."""
        self.darkness_lbl.config(text=f"{self.darkness_var.get():.0f}%")
        self.focus_lbl.config(text=f"{self.focus_var.get():.0f}%")

    def _on_slider_release(self):
        """Al soltar el slider: analiza una sola vez (no cada porcentaje)."""
        self._update_slider_labels()
        if self.drops_path:
            self._run_analysis()

    def _run_analysis(self):
        if not self.drops_path:
            return
        self._show_loading("Analizando…")
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
        self._hide_loading()
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
        base = min(cw / iw, ch / ih)          # escala de ajuste a la ventana
        scale = base * self.drops_zoom        # escala efectiva con zoom
        dw, dh = iw * scale, ih * scale

        # Limitar el desplazamiento para que la imagen nunca deje hueco vacío:
        # si es más grande que el canvas, solo se puede mover hasta tocar el
        # borde; si es más pequeña, queda centrada.
        lim_x = max(0.0, (dw - cw) / 2)
        lim_y = max(0.0, (dh - ch) / 2)
        self.drops_pan[0] = max(-lim_x, min(lim_x, self.drops_pan[0]))
        self.drops_pan[1] = max(-lim_y, min(lim_y, self.drops_pan[1]))

        new_size = (max(int(dw), 1), max(int(dh), 1))
        img = img.resize(new_size, Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        self._photo_refs["drops"] = photo
        canvas.delete("all")
        cx = cw / 2 + self.drops_pan[0]
        cy = ch / 2 + self.drops_pan[1]
        canvas.create_image(cx, cy, image=photo, anchor=tk.CENTER)
        if hasattr(self, "zoom_lbl"):
            self.zoom_lbl.config(text=f"{self.drops_zoom * 100:.0f}%")

    def _reset_zoom(self):
        self.drops_zoom = 1.0
        self.drops_pan = [0.0, 0.0]
        self._refresh_drops_image()

    def _apply_zoom(self, new_zoom, pivot_x, pivot_y):
        """Cambia el zoom manteniendo fijo el punto (pivot) indicado."""
        new_zoom = min(40.0, max(1.0, new_zoom))
        if new_zoom == self.drops_zoom:
            return
        cw = max(self.drops_canvas.winfo_width(), 1)
        ch = max(self.drops_canvas.winfo_height(), 1)
        cx = cw / 2 + self.drops_pan[0]
        cy = ch / 2 + self.drops_pan[1]
        ratio = new_zoom / self.drops_zoom
        self.drops_pan[0] = (cx + (cx - pivot_x) * (ratio - 1)) - cw / 2
        self.drops_pan[1] = (cy + (cy - pivot_y) * (ratio - 1)) - ch / 2
        self.drops_zoom = new_zoom
        self._refresh_drops_image()

    def _zoom_by(self, factor):
        """Zoom desde un botón, centrado en el medio de la imagen."""
        if not self.result:
            return
        cw = max(self.drops_canvas.winfo_width(), 1)
        ch = max(self.drops_canvas.winfo_height(), 1)
        self._apply_zoom(self.drops_zoom * factor, cw / 2, ch / 2)

    def _on_zoom(self, event):
        if not self.result:
            return
        # Dirección de la rueda (Windows usa event.delta; Linux usa num 4/5)
        if getattr(event, "num", None) == 5 or getattr(event, "delta", 0) < 0:
            factor = 1 / 1.1
        else:
            factor = 1.1
        self._apply_zoom(self.drops_zoom * factor, event.x, event.y)

    def _on_pan_start(self, event):
        self._pan_anchor = (event.x, event.y, self.drops_pan[0], self.drops_pan[1])

    def _on_pan_move(self, event):
        if not self._pan_anchor or not self.result:
            return
        x0, y0, p0x, p0y = self._pan_anchor
        self.drops_pan[0] = p0x + (event.x - x0)
        self.drops_pan[1] = p0y + (event.y - y0)
        self._refresh_drops_image()  # _refresh aplica el límite del desplazamiento

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

    # ----------------------------------------------------- pantalla de carga
    def _show_loading(self, text="Cargando…"):
        """Pantalla de carga con fondo SEMITRANSPARENTE (atenúa la app sin
        quedar en negro) y una tarjeta OPACA al centro con el logo y la barra.
        Se usan dos ventanas: el atenuador con LOADING_ALPHA y la tarjeta sin
        transparencia, para que el logo y la barra se vean nítidos."""
        if getattr(self, "_dimmer", None) is None or \
                not self._dimmer.winfo_exists():
            # 1) Atenuador semitransparente (solo oscurece el fondo)
            self._dimmer = tk.Toplevel(self)
            self._dimmer.overrideredirect(True)
            self._dimmer.transient(self)
            try:
                self._dimmer.attributes("-alpha", LOADING_ALPHA)
            except tk.TclError:
                pass
            self._dimmer.configure(bg="#000000")

            # 2) Tarjeta opaca con el contenido
            self._loading = tk.Toplevel(self)
            self._loading.overrideredirect(True)
            self._loading.transient(self)
            self._loading.configure(bg="#1e1e1e",
                                    highlightbackground="#444",
                                    highlightthickness=1)
            tk.Label(self._loading, text="⏳", fg="white", bg="#1e1e1e",
                     font=("Segoe UI", 28)).pack(padx=30, pady=(18, 4))
            self._loading_lbl = tk.Label(self._loading, text=text, fg="white",
                                         bg="#1e1e1e",
                                         font=("Segoe UI", 14, "bold"))
            self._loading_lbl.pack()
            self._loading_pb = ttk.Progressbar(self._loading,
                                               mode="indeterminate", length=240)
            self._loading_pb.pack(padx=30, pady=(12, 20))

        self._loading_lbl.config(text=text)
        self.update_idletasks()
        x, y = self.winfo_rootx(), self.winfo_rooty()
        w, h = self.winfo_width(), self.winfo_height()

        # Atenuador cubre toda la ventana
        self._dimmer.geometry(f"{w}x{h}+{x}+{y}")
        self._dimmer.deiconify()
        self._dimmer.lift()

        # Tarjeta centrada y por encima del atenuador
        self._loading.deiconify()
        self._loading.update_idletasks()
        cw_, ch_ = self._loading.winfo_width(), self._loading.winfo_height()
        self._loading.geometry(
            f"+{x + (w - cw_) // 2}+{y + (h - ch_) // 2}")
        self._loading.lift()
        self._loading_pb.start(12)
        self.update_idletasks()

    def _hide_loading(self):
        if getattr(self, "_loading", None) is not None and \
                self._loading.winfo_exists():
            self._loading_pb.stop()
            self._loading.withdraw()
        if getattr(self, "_dimmer", None) is not None and \
                self._dimmer.winfo_exists():
            self._dimmer.withdraw()


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
