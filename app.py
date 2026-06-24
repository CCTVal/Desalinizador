"""
Aplicación de escritorio (Tkinter) para la detección de gotas del desalinizador.

Estilo CCTVal: fondo azul degradado con arcos, tarjetas blancas redondeadas,
botones y sliders dibujados a mano (canvas) y un flujo por PANTALLAS:

  1. Calibración  -> subir la foto de la regla (con ejemplo de imagen correcta).
  2. Gotas        -> subir la foto de gotas.
  3. Resultados   -> imagen anotada, histograma, sliders y estadísticas.

Para generar el ejecutable .exe ver build.bat / README_APP.md.
"""

import os
import sys
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox

import numpy as np
from PIL import Image, ImageTk, ImageDraw, ImageFont, ImageFilter

# Arrastrar-y-soltar opcional (si tkinterdnd2 está instalado).
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    _HAS_DND = True
except Exception:
    _HAS_DND = False


APP_TITLE = "Análisis de tamaño de gota"
UNIT_TO_UM = {"mm": 1000.0, "cm": 10000.0}

# ------------------------------------------------------------------ paleta
BG_TOP = (0, 116, 255)     # #0074ff azul brillante del glow (centro-arriba)
BG_BOT = (46, 49, 198)     # #2e31c6 índigo profundo (bordes)
CARD = "#ffffff"
HEAD_BLUE = "#2e31c6"      # títulos (índigo CCTVal)
PRIMARY = "#2e31c6"        # botones de acción (Subir / Analizar / Cargar)
PRIMARY_ACTIVE = "#24268f"
ACCENT = "#0074ff"         # checks azules, riel del slider, barras
GREEN = "#22b07d"          # checks del ejemplo
MUTED = "#8a8f98"
INK = "#33373f"
BORDER = "#cfd3da"
TRACK = "#dfe3ea"
LIGHT_BTN = "#e9ebef"
LIGHT_BTN_ACTIVE = "#dde0e6"
GHOST_ACTIVE = "#f1f2ff"

HEADER_H = 150
RADIUS = 26
CARD_PAD = 28
CARD_GAP = 26
FILETYPES = [("Imágenes", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff"),
             ("Todos los archivos", "*.*")]

_MPL_CACHE = None


def _matplotlib_tk():
    """Carga matplotlib solo cuando se abre la pantalla de resultados."""
    global _MPL_CACHE
    if _MPL_CACHE is None:
        import matplotlib
        matplotlib.use("TkAgg")
        try:
            import matplotlib.font_manager as fm
            for p in _font_paths():
                fm.fontManager.addfont(p)
            matplotlib.rcParams["font.family"] = FONT
        except Exception:
            pass
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        _MPL_CACHE = (Figure, FigureCanvasTkAgg)
    return _MPL_CACHE


def _detect_ruler_spacing(*args, **kwargs):
    from detector import detect_ruler_spacing
    return detect_ruler_spacing(*args, **kwargs)


def _analyze_image(*args, **kwargs):
    from detector import analyze_image
    return analyze_image(*args, **kwargs)


def resource_path(name):
    """Ruta de un recurso, compatible con el .exe de PyInstaller."""
    base = getattr(sys, "_MEIPASS",
                   os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


FONT = "Segoe UI"      # familia tipográfica (se ajusta a Poppins al cargar)
_FONT_DIR = resource_path(os.path.join("assets", "fonts"))
_POPPINS = {
    "regular": "Poppins-Regular.ttf",
    "medium": "Poppins-Medium.ttf",
    "semibold": "Poppins-SemiBold.ttf",
    "bold": "Poppins-Bold.ttf",
}


def _font_paths():
    return [os.path.join(_FONT_DIR, f) for f in _POPPINS.values()
            if os.path.exists(os.path.join(_FONT_DIR, f))]


def load_fonts():
    """Carga Poppins de forma privada al proceso (Windows) y la registra en
    matplotlib. Ajusta FONT a 'Poppins' si lo logra; si no, deja 'Segoe UI'."""
    global FONT
    paths = _font_paths()
    if not paths:
        return FONT
    ok = False
    if sys.platform == "win32":
        import ctypes
        for p in paths:
            if ctypes.windll.gdi32.AddFontResourceExW(ctypes.c_wchar_p(p),
                                                      0x10, 0):
                ok = True
    if ok:
        FONT = "Poppins"
    return FONT


def _font(size, bold=False):
    """Fuente PIL (para el logo); prefiere Poppins empaquetada."""
    candidates = ([_POPPINS["bold"], "segoeuib.ttf"] if bold
                  else [_POPPINS["regular"], "segoeui.ttf"])
    for n in candidates:
        for path in (os.path.join(_FONT_DIR, n), n):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


_ATOM_CACHE = None


def _atom_watermark():
    """Carga (y cachea) el átomo de CCTVal para usarlo de marca de agua."""
    global _ATOM_CACHE
    if _ATOM_CACHE is None:
        p = resource_path(os.path.join("assets", "cctval_atom.png"))
        _ATOM_CACHE = Image.open(p).convert("RGBA") if os.path.exists(p) \
            else False
    return _ATOM_CACHE


def _make_gradient(w, h):
    """Fondo CCTVal: azul royal con glow radial, el átomo gigante tenue a la
    izquierda y arcos concéntricos muy sutiles a la derecha."""
    azure = np.array(BG_TOP, dtype=np.float32)    # #0074ff
    indigo = np.array(BG_BOT, dtype=np.float32)   # #2e31c6
    # Degradado lineal en diagonal entre exactamente los dos colores de marca:
    # esquina superior-izq = #2e31c6 (índigo), inferior-der = #0074ff (azul).
    gx = np.linspace(0.0, 1.0, w)[None, :]
    gy = np.linspace(0.0, 1.0, h)[:, None]
    t = np.clip(0.5 * gx + 0.5 * gy, 0.0, 1.0)[..., None]
    arr = (indigo * (1 - t) + azure * t).astype("uint8")
    img = Image.fromarray(arr, "RGB").convert("RGBA")

    # Marca de agua: átomo gigante de CCTVal sangrando por el borde izquierdo.
    atom = _atom_watermark()
    if atom:
        ah = int(h * 1.05)
        aw = int(atom.width * ah / atom.height)
        big = atom.resize((aw, ah), Image.LANCZOS)
        faint = big.split()[3].point(lambda v: int(v * 0.10))
        big.putalpha(faint)
        img.alpha_composite(big, (int(-aw * 0.34), int((h - ah) / 2)))

    # Arcos concéntricos lejanos a la derecha, apenas visibles.
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    step = max(150, int(min(w, h) * 0.22))
    for r in range(step, int(max(w, h) * 1.4), step):
        od.ellipse([w * 0.96 - r, h * 0.10 - r, w * 0.96 + r, h * 0.10 + r],
                   outline=(255, 255, 255, 12), width=2)
    overlay = overlay.filter(ImageFilter.GaussianBlur(0.8))
    return Image.alpha_composite(img, overlay).convert("RGB")


def _make_brand(atom_d=46):
    """Logo: átomo (3 elipses giradas) + palabra 'CCTVal', en blanco."""
    white = (255, 255, 255, 255)
    atom = Image.new("RGBA", (atom_d, atom_d), (0, 0, 0, 0))
    for ang in (0, 60, 120):
        layer = Image.new("RGBA", (atom_d, atom_d), (0, 0, 0, 0))
        ImageDraw.Draw(layer).ellipse(
            [2, atom_d * 0.34, atom_d - 2, atom_d * 0.66],
            outline=white, width=3)
        atom = Image.alpha_composite(
            atom, layer.rotate(ang, resample=Image.BICUBIC,
                               center=(atom_d / 2, atom_d / 2)))
    d = ImageDraw.Draw(atom)
    r = atom_d * 0.085
    d.ellipse([atom_d / 2 - r, atom_d / 2 - r,
               atom_d / 2 + r, atom_d / 2 + r], fill=white)

    font = _font(40, bold=True)
    text = "CCTVal"
    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bbox = tmp.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    gap = 14
    W = atom_d + gap + tw
    H = max(atom_d, th + 8)
    brand = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    brand.paste(atom, (0, (H - atom_d) // 2), atom)
    ImageDraw.Draw(brand).text((atom_d + gap, (H - th) // 2 - bbox[1]),
                               text, font=font, fill=white)
    return brand


def _round_pts(x0, y0, x1, y1, r):
    """Puntos para un rectángulo redondeado (usar con smooth=True)."""
    return [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
            x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]


CARD_MARGIN = 30   # margen alrededor de la tarjeta para que quepa la sombra


def _make_card(cw, ch, radius=RADIUS, margin=CARD_MARGIN):
    """Tarjeta blanca con esquinas redondeadas antialiased y sombra difuminada,
    como imagen RGBA (se compone sobre el degradado). El (0,0) de la tarjeta
    queda en (margin, margin) dentro de la imagen devuelta."""
    cw, ch = int(round(cw)), int(round(ch))
    W, H = cw + 2 * margin, ch + 2 * margin
    # Sombra: rectángulo redondeado oscuro, desplazado y desenfocado.
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [margin, margin + 8, margin + cw, margin + ch + 8],
        radius=radius, fill=(18, 22, 86, 105))
    img = shadow.filter(ImageFilter.GaussianBlur(13))
    # Tarjeta blanca nítida encima.
    ImageDraw.Draw(img).rounded_rectangle(
        [margin, margin, margin + cw, margin + ch],
        radius=radius, fill=(255, 255, 255, 255))
    return img


def _fit(pil_img, box_w, box_h):
    iw, ih = pil_img.size
    s = min(box_w / iw, box_h / ih)
    return pil_img.resize((max(int(iw * s), 1), max(int(ih * s), 1)),
                          Image.LANCZOS)


# --------------------------------------------------------- mini-componentes
def _tint(hex_color, t):
    """Mezcla hex_color hacia blanco (t=0 original … t=1 blanco)."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return "#%02x%02x%02x" % (int(r + (255 - r) * t),
                              int(g + (255 - g) * t),
                              int(b + (255 - b) * t))


def check_badge(parent, d=20, color=PRIMARY, bg=CARD):
    """Círculo con check blanco y un halo pálido del mismo color (mockup)."""
    c = tk.Canvas(parent, width=d, height=d, bg=bg, highlightthickness=0)
    halo = _tint(color, 0.74)
    c.create_oval(0, 0, d - 1, d - 1, fill=halo, outline=halo)
    m = d * 0.16
    c.create_oval(m, m, d - m, d - m, fill=color, outline=color)
    c.create_line(d * 0.31, d * 0.52, d * 0.44, d * 0.66,
                  fill="white", width=2)
    c.create_line(d * 0.44, d * 0.66, d * 0.70, d * 0.36,
                  fill="white", width=2)
    return c


def doc_icon(parent, bg=CARD):
    """Ícono de documento (página gris simple, como en el mockup)."""
    w, h = 20, 24
    c = tk.Canvas(parent, width=w, height=h, bg=bg, highlightthickness=0)
    c.create_polygon(4, 2, 12, 2, 16, 6, 16, 22, 4, 22,
                     fill="", outline=MUTED, width=1.3)
    c.create_line(12, 2, 12, 6, fill=MUTED, width=1.3)
    c.create_line(12, 6, 16, 6, fill=MUTED, width=1.3)
    for yy in (11, 14, 17):
        c.create_line(7, yy, 13, yy, fill="#c4c8d0", width=1)
    return c


def gear_icon(parent, d=16, bg=CARD, color=MUTED):
    """Ícono de engranaje (⚙) gris dibujado en canvas."""
    import math
    c = tk.Canvas(parent, width=d, height=d, bg=bg, highlightthickness=0)
    cx = cy = d / 2
    R, tooth, r = d * 0.30, d * 0.12, d * 0.16
    for k in range(8):
        a = math.radians(k * 45)
        c.create_line(cx + math.cos(a) * R, cy + math.sin(a) * R,
                      cx + math.cos(a) * (R + tooth),
                      cy + math.sin(a) * (R + tooth),
                      fill=color, width=2)
    c.create_oval(cx - R, cy - R, cx + R, cy + R, outline=color, width=1.4)
    c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=color, width=1.4)
    return c


def help_icon(parent, d=15, bg=CARD):
    c = tk.Canvas(parent, width=d, height=d, bg=bg, highlightthickness=0)
    c.create_oval(1, 1, d - 1, d - 1, outline=MUTED, width=1)
    c.create_text(d / 2, d / 2 + 0.5, text="?", fill=MUTED,
                  font=(FONT, 8, "bold"))
    return c


def upload_badge(parent, d=30, bg=CARD):
    """Círculo azul pálido con ícono de subida (bandeja + flecha) azul oscuro."""
    c = tk.Canvas(parent, width=d, height=d, bg=bg, highlightthickness=0)
    c.create_oval(1, 1, d - 1, d - 1, fill="#e7ecfb", outline="#e7ecfb")
    cx = d / 2
    col = PRIMARY
    # flecha hacia arriba
    c.create_line(cx, d * 0.28, cx, d * 0.58, fill=col, width=2)
    c.create_line(cx, d * 0.28, cx - 4, d * 0.40, fill=col, width=2)
    c.create_line(cx, d * 0.28, cx + 4, d * 0.40, fill=col, width=2)
    # bandeja abierta por arriba
    c.create_line(d * 0.30, d * 0.56, d * 0.30, d * 0.72, fill=col, width=2)
    c.create_line(d * 0.30, d * 0.72, d * 0.70, d * 0.72, fill=col, width=2)
    c.create_line(d * 0.70, d * 0.72, d * 0.70, d * 0.56, fill=col, width=2)
    return c


class RoundButton(tk.Canvas):
    """Botón con esquinas redondeadas dibujado en un canvas, con hover."""

    _STYLES = {
        # Primario: índigo CCTVal con texto blanco.
        "primary": dict(fill=PRIMARY, hover=PRIMARY_ACTIVE, fg="white",
                        outline=PRIMARY, h=44, padx=26, font=(10, True)),
        # Secundario: blanco con borde y texto azul brillante.
        "ghost": dict(fill=CARD, hover="#e8f2ff", fg=ACCENT,
                      outline=ACCENT, h=44, padx=26, font=(10, False)),
        # Light: fondo azul claro con texto índigo (zoom / Elegir archivos).
        "light": dict(fill="#e7ecfb", hover="#d8e0fb", fg=PRIMARY,
                      outline="#e7ecfb", h=36, padx=18, font=(9, True)),
    }

    def __init__(self, master, text, command=None, kind="primary",
                 bg=CARD, min_width=0):
        s = self._STYLES[kind]
        self._s = s
        self.command = command
        font = (FONT, s["font"][0],
                "bold" if s["font"][1] else "normal")
        self._font = font
        tw = tkfont.Font(font=font).measure(text)
        w = max(min_width, tw + 2 * s["padx"])
        h = s["h"]
        super().__init__(master, width=w, height=h, bg=bg,
                         highlightthickness=0, cursor="hand2")
        self._bw, self._bh, self._text = w, h, text
        self._hover = False
        self._draw()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _draw(self):
        self.delete("all")
        s = self._s
        fill = s["hover"] if self._hover else s["fill"]
        r = min(self._bh / 2, 14)
        self.create_polygon(_round_pts(1, 1, self._bw - 1, self._bh - 1, r),
                            fill=fill, outline=s["outline"], width=1,
                            smooth=True)
        self.create_text(self._bw / 2, self._bh / 2, text=self._text,
                         fill=s["fg"], font=self._font)

    def _on_enter(self, _):
        self._hover = True
        self._draw()

    def _on_leave(self, _):
        self._hover = False
        self._draw()

    def _on_click(self, _):
        if self.command:
            self.command()


class Slider(tk.Canvas):
    """Slider tipo cápsula (mockup): contorno lavanda, un punto índigo en cada
    extremo, handle de barra vertical índigo y % bajo el handle."""

    RAIL = "#aeb9ee"   # contorno lavanda de la cápsula

    def __init__(self, master, variable, on_release=None, width=380, bg=CARD):
        super().__init__(master, width=width, height=46, bg=bg,
                         highlightthickness=0)
        self.var = variable
        self.on_release = on_release
        self._sw = width
        self._pad = 12
        self._ty = 18      # centro vertical de la cápsula
        self._ph = 8       # mitad de la altura de la cápsula
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Button-1>", self._set_from_event)
        self.bind("<B1-Motion>", self._set_from_event)
        self.bind("<ButtonRelease-1>", self._release)
        self._draw()

    def _width(self):
        w = self.winfo_width()
        return w if w > 1 else self._sw

    def _frac(self):
        return max(0.0, min(1.0, self.var.get() / 100.0))

    def _ends(self, w):
        ph = self._ph
        return self._pad + ph, w - self._pad - ph

    def _draw(self):
        self.delete("all")
        w = self._width()
        ph, ty = self._ph, self._ty
        x0, x1 = self._ends(w)
        hx = x0 + self._frac() * (x1 - x0)
        rail, ink = self.RAIL, PRIMARY
        # cápsula (track): lados rectos + dos semicírculos en los extremos
        self.create_line(x0, ty - ph, x1, ty - ph, fill=rail, width=1.6)
        self.create_line(x0, ty + ph, x1, ty + ph, fill=rail, width=1.6)
        self.create_arc(x0 - ph, ty - ph, x0 + ph, ty + ph, start=90,
                        extent=180, style=tk.ARC, outline=rail, width=1.6)
        self.create_arc(x1 - ph, ty - ph, x1 + ph, ty + ph, start=-90,
                        extent=180, style=tk.ARC, outline=rail, width=1.6)
        # puntos índigo en los extremos
        for dx in (x0, x1):
            self.create_oval(dx - 3, ty - 3, dx + 3, ty + 3,
                             fill=ink, outline=ink)
        # handle: barra vertical índigo
        bh = 13
        self.create_line(hx, ty - bh, hx, ty + bh, fill=ink, width=3,
                         capstyle=tk.ROUND)
        # etiquetas
        ly = ty + ph + 12
        self.create_text(self._pad, ly, text="0%", fill=MUTED, anchor=tk.W,
                         font=(FONT, 8))
        self.create_text(w - self._pad, ly, text="100%", fill=MUTED,
                         anchor=tk.E, font=(FONT, 8))
        self.create_text(hx, ly, text=f"{self.var.get():.0f}%", fill=INK,
                         font=(FONT, 8, "bold"))

    def _set_from_event(self, event):
        w = self._width()
        x0, x1 = self._ends(w)
        frac = (event.x - x0) / max(1, (x1 - x0))
        self.var.set(round(max(0.0, min(1.0, frac)) * 100))
        self._draw()

    def _release(self, _):
        if self.on_release:
            self.on_release()


class UnitToggle(tk.Canvas):
    """Control segmentado (mm / cm) estilizado."""

    def __init__(self, master, variable, options=("mm", "cm"), bg=CARD):
        self.opts = list(options)
        self.var = variable
        self.segw, self.segh = 44, 30
        w = self.segw * len(self.opts)
        super().__init__(master, width=w, height=self.segh, bg=bg,
                         highlightthickness=0, cursor="hand2")
        self._tw = w
        self.bind("<Button-1>", self._click)
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self._tw, self.segh
        self.create_polygon(_round_pts(1, 1, w - 1, h - 1, h / 2 - 1),
                            smooth=True, fill="#eef0f4", outline=BORDER,
                            width=1)
        sel = self.var.get()
        for i, o in enumerate(self.opts):
            x0 = 1 + i * self.segw
            x1 = x0 + self.segw
            if o == sel:
                self.create_polygon(
                    _round_pts(x0 + 1, 3, x1 - 1, h - 3, h / 2 - 3),
                    smooth=True, fill=ACCENT, outline=ACCENT)
            self.create_text((x0 + x1) / 2, h / 2, text=o,
                             fill="white" if o == sel else MUTED,
                             font=(FONT, 9, "bold"))

    def _click(self, event):
        i = max(0, min(len(self.opts) - 1, int(event.x // self.segw)))
        self.var.set(self.opts[i])
        self._draw()


def styled_entry(parent, textvariable, width=5):
    """Entry con borde fino redondeado (sin el relieve clásico de Tk)."""
    wrap = tk.Frame(parent, bg=BORDER)
    e = tk.Entry(wrap, textvariable=textvariable, width=width, bd=0,
                 relief="flat", justify=tk.CENTER, bg="white", fg=INK,
                 font=(FONT, 10))
    e.pack(padx=1, pady=1, ipady=4)
    return wrap


class DropZone(tk.Canvas):
    """Zona de carga: borde punteado redondeado, clic para elegir y (si está
    disponible) arrastrar-y-soltar."""

    def __init__(self, master, on_file, width=430, height=158):
        super().__init__(master, width=width, height=height, bg=CARD,
                         highlightthickness=0, cursor="hand2")
        self.on_file = on_file
        inner = tk.Frame(self, bg=CARD)
        title = tk.Frame(inner, bg=CARD)
        title.pack()
        tk.Label(title, text="Sube o arrastra", bg=CARD, fg=INK,
                 font=(FONT, 11, "bold")).pack(side=tk.LEFT)
        tk.Label(title, text=" tus archivos aquí", bg=CARD, fg=INK,
                 font=(FONT, 11)).pack(side=tk.LEFT)
        tk.Label(inner, text="(Max. file size 20MB)", bg=CARD, fg=MUTED,
                 font=(FONT, 9)).pack(pady=(2, 12))
        RoundButton(inner, "Elegir archivos", command=self._choose,
                    kind="light").pack()
        self._win = self.create_window(width / 2, height / 2, window=inner)
        self.bind("<Configure>", self._draw)
        self.bind("<Button-1>", lambda e: self._choose())
        if _HAS_DND:
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self._on_drop)

    def _draw(self, event=None):
        self.delete("border")
        w, h = self.winfo_width(), self.winfo_height()
        self.create_polygon(_round_pts(3, 3, w - 3, h - 3, 16), smooth=True,
                            fill="", outline=BORDER, width=1, dash=(5, 4),
                            tags="border")
        self.coords(self._win, w / 2, h / 2)
        self.tag_raise(self._win)

    def _choose(self):
        path = filedialog.askopenfilename(title="Seleccionar imagen",
                                          filetypes=FILETYPES)
        if path:
            self.on_file(path)

    def _on_drop(self, event):
        data = event.data.strip()
        path = data.split("} {")[0].strip("{}")
        if path:
            self.on_file(path)


_Base = TkinterDnD.Tk if _HAS_DND else tk.Tk


class App(_Base):
    def __init__(self):
        super().__init__()
        self.withdraw()
        load_fonts()
        self.title("CCTVal · " + APP_TITLE)
        self._set_window_icon()
        self._set_initial_geometry()
        self.configure(bg="#10268f")

        self.calib_path = None
        self.drops_path = None
        self.um_per_pixel = None
        self.ruler = None
        self.result = None
        self._photo = {}
        self._cards = []
        self._bg_size = (0, 0)

        self.dist_var = tk.StringVar(value="1")
        self.unit_var = tk.StringVar(value="mm")
        self.darkness_var = tk.DoubleVar(value=27.0)
        self.focus_var = tk.DoubleVar(value=80.0)

        self.drops_zoom = 1.0
        self.drops_pan = [0.0, 0.0]
        self._pan_anchor = None
        self._drops_src = None          # imagen PIL cacheada
        self._drops_src_arr = None      # arr de origen para invalidar cache
        self._drops_settle_job = None   # redibujado de calidad diferido

        self._card_cache = {}
        self._loading = None
        self._switching = False
        self._screen = "calibration"
        self._compact_results = False
        # Dos versiones del logo: grande/bajo para pantallas con cabecera libre,
        # y compacto/arriba para resultados (su tarjeta ocupa casi toda la altura).
        self._brand_big = self._load_brand(100)
        self._brand_small = self._load_brand(66)
        self._brand = self._brand_big
        self.bg = tk.Canvas(self, highlightthickness=0)
        self.bg.pack(fill=tk.BOTH, expand=True)
        self._scrollable = False
        self.bind_all("<MouseWheel>", self._on_page_wheel)
        self.bind_all("<Button-4>", self._on_page_wheel)
        self.bind_all("<Button-5>", self._on_page_wheel)
        self.bind("<Configure>", lambda e: self._relayout())
        self.show_calibration()
        self.update_idletasks()
        self.deiconify()

    # --------------------------------------------------------- fondo / layout
    def _set_initial_geometry(self):
        """Ajusta la ventana al monitor para evitar que parta cortada."""
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w = max(980, min(1300, sw - 80))
        h = max(620, min(860, sh - 90))
        x = max((sw - w) // 2, 0)
        y = max((sh - h) // 2, 0)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(min(980, max(sw - 80, 760)),
                     min(620, max(sh - 120, 520)))

    def _relayout(self, event=None):
        if getattr(self, "_switching", False):
            return
        W, H = self.winfo_width(), self.winfo_height()
        if W <= 1 or H <= 1:
            return
        self._resize_result_widgets(W, H)
        self._draw_header(W)
        if not self._cards:
            self._paint_gradient(W, H)
            return
        self.bg.delete("cardbg")
        self.bg.update_idletasks()
        sizes = [(c["frame"].winfo_reqwidth(), c["frame"].winfo_reqheight())
                 for c in self._cards]
        widths = [w + 2 * CARD_PAD for (w, h) in sizes]
        total = sum(widths) + CARD_GAP * (len(self._cards) - 1)
        stack = len(self._cards) > 1 and total > W - 40
        if stack:
            content_h = sum(h + 2 * CARD_PAD for (w, h) in sizes) + \
                CARD_GAP * (len(self._cards) - 1)
        else:
            content_h = max(h + 2 * CARD_PAD for (w, h) in sizes)
        header_h = 120 if self._screen == "results" else HEADER_H
        bottom_gap = 34 if self._screen == "results" else CARD_MARGIN * 2
        y0 = max(header_h + (H - header_h - content_h - bottom_gap) / 2,
                 header_h - 20)
        scroll_h = max(H, int(y0 + content_h + CARD_MARGIN * 2))
        self._paint_gradient(W, scroll_h)

        rects = []
        x = (W - total) / 2 if not stack else None
        y = y0
        for c, (w, h), cw in zip(self._cards, sizes, widths):
            ch = h + 2 * CARD_PAD
            if stack:
                x = max((W - cw) / 2, CARD_MARGIN)
            # Tarjeta como imagen PIL: esquinas suaves + sombra difuminada.
            key = (cw, ch)
            img = self._card_cache.get(key)
            if img is None:
                img = ImageTk.PhotoImage(_make_card(cw, ch))
                self._card_cache[key] = img
            self.bg.create_image(x - CARD_MARGIN, y - CARD_MARGIN,
                                 anchor=tk.NW, image=img, tags="cardbg")
            self.bg.itemconfigure(c["win"], anchor="center")
            self.bg.coords(c["win"], x + CARD_PAD + w / 2,
                           y + CARD_PAD + h / 2)
            self.bg.tag_raise(c["win"])
            rects.append((x, y, cw, ch))
            if stack:
                y += ch + CARD_GAP
            else:
                x += cw + CARD_GAP

        # Línea conectora entre la tarjeta principal y la de ejemplo.
        if len(rects) == 2 and not stack:
            x0, y0a, cw0, _ = rects[0]
            x1, y1a, _, _ = rects[1]
            sx, sy = x0 + cw0, y0a + CARD_PAD + 52
            ex, ey = x1, y1a + 28
            self.bg.create_line(sx, sy, ex, ey, fill="#8aa9ef", width=1,
                                tags="cardbg")
            self.bg.tag_lower("cardbg")
            self.bg.tag_lower("grad")
        else:
            self.bg.tag_lower("cardbg")
            self.bg.tag_lower("grad")

        self._scrollable = scroll_h > H + 2
        self.bg.configure(scrollregion=(0, 0, W, scroll_h))
        if not self._scrollable:
            self.bg.yview_moveto(0)

    def _paint_gradient(self, W, H):
        if (W, H) != self._bg_size:
            self._photo["grad"] = ImageTk.PhotoImage(_make_gradient(W, H))
            self._bg_size = (W, H)
            self.bg.delete("grad")
            self.bg.create_image(0, 0, anchor=tk.NW, image=self._photo["grad"],
                                 tags="grad")
            self.bg.tag_lower("grad")

    def _on_page_wheel(self, event):
        if not self._scrollable:
            return
        if getattr(self, "drops_canvas", None) is not None and \
                event.widget is self.drops_canvas:
            return
        if getattr(event, "num", None) == 4:
            units = -3
        elif getattr(event, "num", None) == 5:
            units = 3
        else:
            units = -1 * int(event.delta / 120) * 3
        self.bg.yview_scroll(units, "units")

    def _resize_result_widgets(self, W, H):
        if self._screen != "results" or not hasattr(self, "drops_canvas"):
            return
        compact = H < 820
        if compact != self._compact_results:
            self._compact_results = compact
            if getattr(self, "result_help_lbl", None) is not None:
                if compact:
                    self.result_help_lbl.pack_forget()
                else:
                    self.result_help_lbl.pack(anchor=tk.W, pady=(4, 0))
            if self.result and hasattr(self, "stats_box"):
                self._refresh_stats()
        canvas_w = max(340, min(520, int(W * 0.38)))
        canvas_h = max(180, min(360, H - 440))
        if int(self.drops_canvas.cget("width")) != canvas_w or \
                int(self.drops_canvas.cget("height")) != canvas_h:
            self.drops_canvas.configure(width=canvas_w, height=canvas_h)
            self._refresh_drops_image()
        if hasattr(self, "fig"):
            fig_w = max(3.2, min(4.8, (W - canvas_w - 220) / 105))
            fig_h = max(2.1, min(3.35, canvas_h / 105))
            self.fig.set_size_inches(fig_w, fig_h, forward=True)
            if hasattr(self, "chart_widget"):
                self.chart_widget.configure(width=int(fig_w * 100),
                                            height=int(fig_h * 100))
            if self.result and hasattr(self, "chart_canvas"):
                self._refresh_chart()

    def _set_window_icon(self):
        """Ícono de la ventana/barra de tareas con el logo de CCTVal."""
        # En Windows la barra de tareas agrupa la app bajo python.exe y muestra
        # SU ícono; declarar un AppUserModelID propio hace que use el de la
        # ventana (el átomo de CCTVal) en vez del logo de Python.
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    "CCTVal.Desalinizador.GotasApp")
            except Exception:
                pass
        ico = resource_path(os.path.join("assets", "cctval_icon.ico"))
        if os.path.exists(ico):
            try:
                self.iconbitmap(default=ico)
            except Exception:
                pass
        png = resource_path(os.path.join("assets", "cctval_icon.png"))
        try:
            src = png if os.path.exists(png) else ico
            self._icon_img = ImageTk.PhotoImage(Image.open(src))
            self.iconphoto(True, self._icon_img)
        except Exception:
            pass

    def _load_brand(self, height=88):
        """Usa el logo oficial (assets/cctval_logo.png, blanco con fondo
        transparente) si existe; si no, dibuja un átomo + 'CCTVal'."""
        for name in ("cctval_logo.png", "logo.png"):
            p = resource_path(os.path.join("assets", name))
            if os.path.exists(p):
                try:
                    img = Image.open(p).convert("RGBA")
                    s = height / img.height
                    img = img.resize((max(int(img.width * s), 1), height),
                                     Image.LANCZOS)
                    return ImageTk.PhotoImage(img)
                except Exception:
                    pass
        return ImageTk.PhotoImage(_make_brand())

    def _draw_header(self, W):
        self.bg.delete("hdr")
        # En resultados la tarjeta sube hasta la cabecera: logo compacto y arriba.
        if self._screen == "results":
            brand, y = self._brand_small, 72
        else:
            brand, y = self._brand_big, 108
        self.bg.create_image(W / 2, y, image=brand, tags="hdr")
        self.bg.tag_raise("hdr")

    # ------------------------------------------------------- tarjetas helpers
    def _clear_cards(self):
        for c in self._cards:
            self.bg.delete(c["win"])
            c["frame"].destroy()
        self._cards = []
        self.bg.delete("cardbg")

    def _new_card(self):
        frame = tk.Frame(self.bg, bg=CARD)
        win = self.bg.create_window(0, 0, window=frame, anchor="center")
        self._cards.append({"frame": frame, "win": win})
        return frame

    def _refresh_layout(self):
        self.update_idletasks()
        self._relayout()

    def _switch_screen(self, build):
        """Construye una pantalla fuera de vista y la muestra ya estabilizada."""
        self._switching = True
        try:
            self.bg.configure(takefocus=0)
            self.bg.pack_forget()
            build()
            self.update_idletasks()
        finally:
            self.bg.pack(fill=tk.BOTH, expand=True)
            self._switching = False
        self._relayout()
        self.update_idletasks()

    def _card_title(self, parent, subtitle):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill=tk.X, anchor=tk.W)
        upload_badge(row).pack(side=tk.LEFT, padx=(0, 10))
        texts = tk.Frame(row, bg=CARD)
        texts.pack(side=tk.LEFT)
        tk.Label(texts, text=APP_TITLE, bg=CARD, fg=HEAD_BLUE,
                 font=(FONT, 13, "bold")).pack(anchor=tk.W)
        sub = tk.Frame(texts, bg=CARD)
        sub.pack(anchor=tk.W)
        tk.Label(sub, text=subtitle, bg=CARD, fg=MUTED,
                 font=(FONT, 9)).pack(side=tk.LEFT)
        help_icon(sub).pack(side=tk.LEFT, padx=4)

    def _file_chip(self, parent, path, on_remove):
        chip = tk.Frame(parent, bg=CARD, highlightbackground=BORDER,
                        highlightthickness=1)
        doc_icon(chip).pack(side=tk.LEFT, padx=(10, 8), pady=8)
        tk.Label(chip, text=os.path.basename(path), bg=CARD, fg=INK,
                 font=(FONT, 10)).pack(side=tk.LEFT, pady=8)
        tk.Button(chip, text="✕", bg=CARD, fg=MUTED, bd=0,
                  activebackground=CARD, cursor="hand2",
                  font=(FONT, 10), command=on_remove).pack(
            side=tk.RIGHT, padx=10)
        tk.Label(chip, text="100%", bg=CARD, fg=MUTED,
                 font=(FONT, 9)).pack(side=tk.RIGHT)
        check_badge(chip, color=PRIMARY).pack(side=tk.RIGHT, padx=6)
        return chip

    # ============================================================ PANTALLA 1
    def show_calibration(self):
        def build():
            self._screen = "calibration"
            self._clear_cards()
            card = self._new_card()
            self._card_title(card, "Selecciona la imagen de calibración")
            DropZone(card, self._on_calib_file, width=420).pack(
                fill=tk.X, pady=(16, 10))
            self.calib_chip = tk.Frame(card, bg=CARD)
            self.calib_chip.pack(fill=tk.X)

            btns = tk.Frame(card, bg=CARD)
            btns.pack(fill=tk.X, pady=(22, 2))
            RoundButton(btns, "Subir", command=self._submit_calibration,
                        kind="primary").pack(side=tk.RIGHT)
            RoundButton(btns, "Cancelar", command=self._clear_calib_file,
                        kind="ghost").pack(side=tk.RIGHT, padx=10)

            # tarjeta lateral: ejemplo
            side = self._new_card()
            head = tk.Frame(side, bg=CARD)
            head.pack(anchor=tk.W)
            gear_icon(head).pack(side=tk.LEFT, padx=(0, 6))
            tk.Label(head, text="Ejemplo de imagen correcta", bg=CARD,
                     fg=HEAD_BLUE, font=(FONT, 10, "bold")).pack(side=tk.LEFT)

            ex = self._example_image(300, 180)
            holder = tk.Label(side, bg="#dfe3ea")
            if ex is not None:
                self._photo["example"] = ex
                holder.configure(image=ex)
            else:
                holder.configure(text="(ejemplo de regla)", fg=MUTED,
                                 width=40, height=10)
            holder.pack(pady=12)
            for txt in ("Regla completamente visible", "Buena iluminación",
                        "Enfoque nítido"):
                row = tk.Frame(side, bg=CARD)
                row.pack(anchor=tk.W, pady=2)
                check_badge(row, color=GREEN).pack(side=tk.LEFT, padx=(0, 8))
                tk.Label(row, text=txt, bg=CARD, fg=INK,
                         font=(FONT, 10)).pack(side=tk.LEFT)

        self._switch_screen(build)

    def _example_image(self, w, h):
        for name in (os.path.join("assets", "ruler_example.jpg"),
                     "test_ruler_real.jpg", "test_ruler.jpg"):
            p = resource_path(name)
            if os.path.exists(p):
                try:
                    return ImageTk.PhotoImage(
                        _fit(Image.open(p).convert("RGB"), w, h))
                except Exception:
                    pass
        return None

    def _on_calib_file(self, path):
        self.calib_path = path
        self._rebuild_chip(self.calib_chip, path, self._clear_calib_file)

    def _clear_calib_file(self):
        self.calib_path = None
        self._rebuild_chip(self.calib_chip, None, None)

    def _rebuild_chip(self, holder, path, on_remove):
        for w in holder.winfo_children():
            w.destroy()
        if path:
            self._file_chip(holder, path, on_remove).pack(fill=tk.X)
        self._refresh_layout()

    def _submit_calibration(self):
        if not self.calib_path:
            messagebox.showwarning("Calibración",
                                   "Primero suba una foto de la regla.")
            return
        path = self.calib_path
        self._run_async(lambda: _detect_ruler_spacing(path),
                        self._on_calibration_done, "Detectando regla…")

    def _on_calibration_done(self, ruler):
        self.ruler = ruler
        if ruler.get("ok"):
            if not self._calibration_dialog(ruler["spacing_px"],
                                            ruler.get("confidence", 0) * 100):
                return  # el usuario canceló
        else:
            self.um_per_pixel = None
            if not messagebox.askyesno(
                    "Sin calibración",
                    "No se detectaron marcas en la regla.\n"
                    "¿Continuar sin calibrar? (los tamaños irán en píxeles)"):
                return
        self.show_drops()

    def _ruler_preview(self, max_w=380, max_h=220):
        """Foto de la regla reescalada con las marcas detectadas dibujadas en
        azul encima (usa tick_segments, en coords de la imagen original)."""
        if not self.calib_path or not self.ruler:
            return None
        try:
            img = Image.open(self.calib_path).convert("RGB")
        except Exception:
            return None
        iw, ih = img.size
        scale = min(max_w / iw, max_h / ih)
        disp = img.resize((max(int(iw * scale), 1), max(int(ih * scale), 1)),
                          Image.LANCZOS)
        draw = ImageDraw.Draw(disp)
        for (p0, p1) in self.ruler.get("tick_segments", []):
            draw.line([p0[0] * scale, p0[1] * scale,
                       p1[0] * scale, p1[1] * scale],
                      fill=(0, 116, 255), width=2)
        return ImageTk.PhotoImage(disp)

    def _calibration_dialog(self, spacing_px, conf):
        """Modal estilizado: pide cuánto vale una división y fija µm/píxel.
        Devuelve True si el usuario acepta."""
        dlg = tk.Toplevel(self)
        dlg.title("Calibración")
        dlg.configure(bg=CARD)
        dlg.transient(self)
        dlg.resizable(False, False)
        try:
            dlg.iconbitmap(default=resource_path(
                os.path.join("assets", "cctval_icon.ico")))
        except Exception:
            pass

        pad = tk.Frame(dlg, bg=CARD)
        pad.pack(padx=28, pady=24)
        tk.Label(pad, text="Regla detectada", bg=CARD, fg=HEAD_BLUE,
                 font=(FONT, 13, "bold")).pack(anchor=tk.W)
        tk.Label(pad, text=f"Separación: {spacing_px:.1f} px  ·  "
                 f"confianza {conf:.0f}%", bg=CARD, fg=MUTED,
                 font=(FONT, 9)).pack(anchor=tk.W, pady=(2, 10))

        # Vista previa de la regla con las marcas detectadas (en azul), para
        # confirmar visualmente que la calibración es correcta.
        prev = self._ruler_preview()
        if prev is not None:
            self._photo["ruler_prev"] = prev
            tk.Label(pad, image=prev, bg="#dfe3ea", bd=0).pack(anchor=tk.W)
            tk.Label(pad, text="Marcas detectadas en azul · verifique que "
                     "coincidan con la regla.", bg=CARD, fg=MUTED,
                     font=(FONT, 8)).pack(anchor=tk.W, pady=(4, 14))

        row = tk.Frame(pad, bg=CARD)
        row.pack(anchor=tk.W)
        tk.Label(row, text="1 división de la regla =", bg=CARD, fg=INK,
                 font=(FONT, 10)).pack(side=tk.LEFT)
        styled_entry(row, self.dist_var).pack(side=tk.LEFT, padx=8)
        UnitToggle(row, self.unit_var).pack(side=tk.LEFT)

        scale_lbl = tk.Label(pad, text="", bg=CARD, fg=ACCENT,
                             font=(FONT, 10, "bold"))
        scale_lbl.pack(anchor=tk.W, pady=(16, 0))

        state = {"ok": False}

        def update_scale(*_):
            try:
                d = float(self.dist_var.get().replace(",", "."))
                if d <= 0:
                    raise ValueError
                upp = d * UNIT_TO_UM[self.unit_var.get()] / spacing_px
                scale_lbl.config(text=f"Escala: {upp:.3f} µm/píxel",
                                 fg=ACCENT)
            except ValueError:
                scale_lbl.config(text="Ingrese un valor válido (> 0)",
                                 fg="#c0392b")

        t1 = self.dist_var.trace_add("write", update_scale)
        t2 = self.unit_var.trace_add("write", update_scale)
        update_scale()

        def close():
            try:
                self.dist_var.trace_remove("write", t1)
                self.unit_var.trace_remove("write", t2)
            except Exception:
                pass
            dlg.destroy()

        def accept():
            try:
                d = float(self.dist_var.get().replace(",", "."))
                if d <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Calibración",
                                       "Indique un valor válido (> 0).")
                return
            self.um_per_pixel = d * UNIT_TO_UM[self.unit_var.get()] / spacing_px
            state["ok"] = True
            close()

        btns = tk.Frame(pad, bg=CARD)
        btns.pack(anchor=tk.E, pady=(20, 0))
        RoundButton(btns, "Aceptar", command=accept,
                    kind="primary").pack(side=tk.RIGHT)
        RoundButton(btns, "Cancelar", command=close,
                    kind="ghost").pack(side=tk.RIGHT, padx=8)

        dlg.protocol("WM_DELETE_WINDOW", close)
        dlg.update_idletasks()
        px = self.winfo_rootx() + (self.winfo_width() - dlg.winfo_width()) // 2
        py = self.winfo_rooty() + (self.winfo_height()
                                   - dlg.winfo_height()) // 2
        dlg.geometry(f"+{px}+{py}")
        dlg.grab_set()
        self.wait_window(dlg)
        return state["ok"]

    # ============================================================ PANTALLA 2
    def show_drops(self):
        def build():
            self._screen = "drops"
            self._clear_cards()
            card = self._new_card()
            self._card_title(card, "Selecciona la imagen de gotas")
            DropZone(card, self._on_drops_file, width=420).pack(
                fill=tk.X, pady=(16, 10))
            self.drops_chip = tk.Frame(card, bg=CARD)
            self.drops_chip.pack(fill=tk.X)
            note = ("Calibrado: tamaños en µm." if self.um_per_pixel
                    else "Sin calibración: tamaños en píxeles.")
            tk.Label(card, text=note, bg=CARD, fg=MUTED,
                     font=(FONT, 9)).pack(anchor=tk.W, pady=(10, 0))
            btns = tk.Frame(card, bg=CARD)
            btns.pack(fill=tk.X, pady=(22, 2))
            RoundButton(btns, "Analizar", command=self._submit_drops,
                        kind="primary").pack(side=tk.RIGHT)
            RoundButton(btns, "Volver", command=self.show_calibration,
                        kind="ghost").pack(side=tk.RIGHT, padx=10)

        self._switch_screen(build)

    def _on_drops_file(self, path):
        self.drops_path = path
        self._rebuild_chip(self.drops_chip, path, self._clear_drops_file)

    def _clear_drops_file(self):
        self.drops_path = None
        self._rebuild_chip(self.drops_chip, None, None)

    def _submit_drops(self):
        if not self.drops_path:
            messagebox.showwarning("Análisis",
                                   "Primero suba una foto de gotas.")
            return
        self.drops_zoom = 1.0
        self.drops_pan = [0.0, 0.0]
        self._run_async(self._analysis_work(), self._on_drops_analyzed,
                        "Analizando gotas…")

    def _on_drops_analyzed(self, res):
        if not res.get("ok"):
            messagebox.showerror("Error", res.get("error", "Error desconocido"))
            return
        self.result = res
        self.show_results()

    # ============================================================ PANTALLA 3
    def show_results(self):
        def build():
            self._screen = "results"
            self._clear_cards()
            card = self._new_card()
            self.result_title = tk.Label(card, text=APP_TITLE.upper(), bg=CARD,
                                         fg=HEAD_BLUE,
                                         font=(FONT, 13, "bold"))
            self.result_title.pack(pady=(0, 10))
            body = tk.Frame(card, bg=CARD)
            body.pack(fill=tk.BOTH, expand=True)

            left = tk.Frame(body, bg=CARD)
            left.pack(side=tk.LEFT, padx=(0, 20))
            self.drops_canvas = tk.Canvas(left, width=500, height=300,
                                          bg="#000", highlightthickness=0)
            self.drops_canvas.pack()
            self.drops_canvas.bind("<Configure>",
                                   lambda e: self._refresh_drops_image())
            self.drops_canvas.bind("<MouseWheel>", self._on_zoom)
            self.drops_canvas.bind("<Button-4>", self._on_zoom)
            self.drops_canvas.bind("<Button-5>", self._on_zoom)
            self.drops_canvas.bind("<ButtonPress-1>", self._on_pan_start)
            self.drops_canvas.bind("<B1-Motion>", self._on_pan_move)
            self.drops_canvas.bind("<Double-Button-1>",
                                   lambda e: self._reset_zoom())

            # Barra de zoom visible (como en la versión anterior)
            zoombar = tk.Frame(left, bg=CARD)
            zoombar.pack(fill=tk.X, pady=(6, 0))
            RoundButton(zoombar, "−", command=lambda: self._zoom_by(1 / 1.25),
                        kind="light").pack(side=tk.LEFT)
            RoundButton(zoombar, "+", command=lambda: self._zoom_by(1.25),
                        kind="light").pack(side=tk.LEFT, padx=6)
            RoundButton(zoombar, "Ajustar", command=self._reset_zoom,
                        kind="light").pack(side=tk.LEFT)
            self.zoom_lbl = tk.Label(zoombar, text="100%", bg=CARD, fg=MUTED,
                                     font=(FONT, 9, "bold"), width=6)
            self.zoom_lbl.pack(side=tk.LEFT, padx=8)
            self.result_help_lbl = tk.Label(
                left,
                text="Rueda: zoom · Arrastrar: mover · Doble clic: ajustar",
                bg=CARD, fg=MUTED, font=(FONT, 8))
            self.result_help_lbl.pack(anchor=tk.W, pady=(4, 0))

            self._slider(left, "OSCURIDAD", self.darkness_var)
            self._slider(left, "ENFOQUE", self.focus_var)
            self._update_zoom_label()

            right = tk.Frame(body, bg=CARD)
            right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            Figure, FigureCanvasTkAgg = _matplotlib_tk()
            self.fig = Figure(figsize=(4.2, 2.4), dpi=100)
            self.fig.patch.set_facecolor(CARD)
            self.ax = self.fig.add_subplot(111)
            self.chart_canvas = FigureCanvasTkAgg(self.fig, master=right)
            self.chart_widget = self.chart_canvas.get_tk_widget()
            RoundButton(right, "Cargar nuevo archivo", command=self.show_drops,
                        kind="primary").pack(side=tk.BOTTOM, anchor=tk.E,
                                             pady=(8, 0))
            self.stats_box = tk.Frame(right, bg=CARD)
            self.stats_box.pack(side=tk.BOTTOM, anchor=tk.W, pady=(8, 4))
            self.chart_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

            self._render_results()

        self._switch_screen(build)

    def _slider(self, parent, label, var):
        wrap = tk.Frame(parent, bg=CARD)
        wrap.pack(fill=tk.X, pady=(8, 0))
        tk.Label(wrap, text=label, bg=CARD, fg=MUTED,
                 font=(FONT, 8, "bold")).pack(anchor=tk.W)
        Slider(wrap, var, on_release=self._on_slider_release,
               width=430).pack(fill=tk.X)

    def _on_slider_release(self):
        if not self.drops_path:
            return
        self._run_async(self._analysis_work(), self._on_slider_analyzed,
                        "Recalculando…")

    def _on_slider_analyzed(self, res):
        if not res.get("ok"):
            messagebox.showerror("Error", res.get("error", "Error desconocido"))
            return
        self.result = res
        self._render_results()

    # ------------------------------------------------------------- análisis
    def _analysis_work(self):
        """Captura los parámetros en el hilo principal y devuelve una función
        sin estado Tk para ejecutar el análisis en un hilo aparte."""
        path = self.drops_path
        darkness = self.darkness_var.get()
        focus = self.focus_var.get()
        upp = self.um_per_pixel
        return lambda: _analyze_image(path, darkness_pct=darkness,
                                      focus_pct=focus, um_per_pixel=upp)

    # ----------------------------------------------------- pantalla de carga
    def _run_async(self, work, on_done, text="Procesando…"):
        """Ejecuta work() en un hilo mostrando la pantalla de carga animada.
        El hilo solo escribe en `box`; el hilo principal hace polling (Tk no es
        seguro entre hilos) y al terminar llama on_done(resultado)."""
        self._show_loading(text)
        box = {}

        def worker():
            try:
                box["value"] = work()
            except Exception as exc:           # noqa: BLE001
                box["error"] = exc
            box["done"] = True

        def poll():
            if not box.get("done"):
                self.after(50, poll)
                return
            if "error" in box:
                self._hide_loading()
                messagebox.showerror("Error", str(box["error"]))
                return
            try:
                on_done(box["value"])
            finally:
                self._hide_loading()

        threading.Thread(target=worker, daemon=True).start()
        self.after(50, poll)

    def _show_loading(self, text="Procesando…"):
        if self._loading:
            self._loading["text"] = text
            return
        W = max(self.winfo_width(), 1)
        H = max(self.winfo_height(), 1)
        cv = tk.Canvas(self, highlightthickness=0, bg="#1b2bb0")
        cv.place(x=0, y=0, relwidth=1, relheight=1)
        self._photo["loading_grad"] = ImageTk.PhotoImage(_make_gradient(W, H))
        cv.create_image(0, 0, anchor=tk.NW, image=self._photo["loading_grad"])
        cv.create_image(W / 2, H / 2 - 78, image=self._brand)
        cv.create_text(W / 2, H / 2 + 82, text=text, fill="white",
                       font=(FONT, 12), tags="ldtext")
        self._loading = {"cv": cv, "angle": 0, "cx": W / 2,
                         "cy": H / 2 + 24, "text": text, "job": None}
        self._spin()

    def _spin(self):
        ld = self._loading
        if not ld:
            return
        cv = ld["cv"]
        cv.delete("spin")
        cx, cy, a, r = ld["cx"], ld["cy"], ld["angle"], 22
        cv.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#8a98da",
                       width=4, tags="spin")
        cv.create_arc(cx - r, cy - r, cx + r, cy + r, start=a, extent=110,
                      style=tk.ARC, outline="white", width=4, tags="spin")
        cv.itemconfigure("ldtext", text=ld["text"])
        ld["angle"] = (a - 20) % 360
        ld["job"] = self.after(35, self._spin)

    def _hide_loading(self):
        ld = self._loading
        if not ld:
            return
        if ld.get("job"):
            try:
                self.after_cancel(ld["job"])
            except Exception:
                pass
        ld["cv"].destroy()
        self._loading = None

    def _render_results(self):
        if not self.result:
            return
        self._refresh_drops_image()
        self._refresh_chart()
        self._refresh_stats()

    def _refresh_stats(self):
        for w in self.stats_box.winfo_children():
            w.destroy()
        res = self.result
        unit = res["unit"]
        compact = getattr(self, "_compact_results", False)
        font_size = 9 if compact else 11
        badge_size = 16 if compact else 20
        row_pady = 1 if compact else 3
        rows = [("Gotas reconocidas: ", f"{res['count']}"),
                ("Tamaño promedio: ", f"{res['mean_width']:.0f} {unit}"),
                ("Desviación estándar: ", f"{res['std_width']:.0f} {unit}")]
        for prefix, value in rows:
            row = tk.Frame(self.stats_box, bg=CARD)
            row.pack(anchor=tk.W, pady=row_pady)
            check_badge(row, d=badge_size).pack(side=tk.LEFT, padx=(0, 8))
            tk.Label(row, text=prefix, bg=CARD, fg=INK,
                     font=(FONT, font_size)).pack(side=tk.LEFT)
            tk.Label(row, text=value, bg=CARD, fg=INK,
                     font=(FONT, font_size, "bold")).pack(side=tk.LEFT)

    def _refresh_chart(self):
        self.ax.clear()
        widths = self.result.get("widths", [])
        unit = self.result.get("unit", "px")
        unit_label = "pixeles" if unit == "px" else unit
        self.ax.set_facecolor(CARD)
        self.ax.set_title("Anchos de gota", fontsize=10, color=INK,
                          fontweight="bold")
        self.ax.set_xlabel(f"Ancho de gota ({unit_label})", fontsize=8,
                           color=MUTED)
        self.ax.set_ylabel("Frecuencia", fontsize=8, color=MUTED)
        self.ax.tick_params(labelsize=7, colors=MUTED, length=0)
        for s in self.ax.spines.values():   # marco completo (caja)
            s.set_visible(True)
            s.set_color(BORDER)
        self.ax.grid(axis="y", color="#eef0f4", linewidth=1)
        self.ax.set_axisbelow(True)
        if widths:
            self.ax.hist(widths, bins=30, color=PRIMARY, edgecolor="white",
                         linewidth=0.5)
        else:
            self.ax.text(0.5, 0.5, "Sin gotas detectadas", ha="center",
                         va="center", transform=self.ax.transAxes, color="#999")
        self.fig.tight_layout()
        self.chart_canvas.draw()

    # ----------------------------------------------------- imagen zoom/pan
    def _refresh_drops_image(self, fast=False):
        if not self.result:
            return
        arr = self.result.get("output_rgb")
        if arr is None:
            return
        canvas = self.drops_canvas
        cw, ch = max(canvas.winfo_width(), 1), max(canvas.winfo_height(), 1)
        if cw <= 1 or ch <= 1:
            return
        # Cachear la imagen PIL; solo reconstruir si cambió el arreglo origen.
        if self._drops_src is None or self._drops_src_arr is not arr:
            self._drops_src = Image.fromarray(arr)
            self._drops_src_arr = arr
        img = self._drops_src
        iw, ih = img.size
        scale = min(cw / iw, ch / ih) * self.drops_zoom
        dw, dh = iw * scale, ih * scale
        lim_x = max(0.0, (dw - cw) / 2)
        lim_y = max(0.0, (dh - ch) / 2)
        self.drops_pan[0] = max(-lim_x, min(lim_x, self.drops_pan[0]))
        self.drops_pan[1] = max(-lim_y, min(lim_y, self.drops_pan[1]))

        # Esquina superior izquierda de la imagen completa sobre el canvas.
        left = cw / 2 + self.drops_pan[0] - dw / 2
        top = ch / 2 + self.drops_pan[1] - dh / 2

        # Recortar SOLO la región que cae dentro del canvas visible: así el
        # redimensionado nunca supera el tamaño del canvas, sin importar el zoom.
        sx0 = max(0.0, -left / scale)
        sy0 = max(0.0, -top / scale)
        sx1 = min(float(iw), (cw - left) / scale)
        sy1 = min(float(ih), (ch - top) / scale)
        if sx1 <= sx0 or sy1 <= sy0:
            canvas.delete("all")
            return
        ix0, iy0 = int(sx0), int(sy0)
        ix1, iy1 = min(iw, int(sx1) + 1), min(ih, int(sy1) + 1)
        crop = img.crop((ix0, iy0, ix1, iy1))
        ow = max(int((ix1 - ix0) * scale), 1)
        oh = max(int((iy1 - iy0) * scale), 1)
        resample = Image.BILINEAR if fast else Image.LANCZOS
        crop = crop.resize((ow, oh), resample)
        self._photo["drops"] = ImageTk.PhotoImage(crop)
        canvas.delete("all")
        canvas.create_image(left + ix0 * scale, top + iy0 * scale,
                            image=self._photo["drops"], anchor=tk.NW)

    def _refresh_drops_fast(self):
        """Redibuja rápido (BILINEAR) y programa un repintado de calidad."""
        self._refresh_drops_image(fast=True)
        if self._drops_settle_job is not None:
            self.after_cancel(self._drops_settle_job)
        self._drops_settle_job = self.after(
            120, lambda: self._refresh_drops_image(fast=False))

    def _update_zoom_label(self):
        if getattr(self, "zoom_lbl", None) and self.zoom_lbl.winfo_exists():
            self.zoom_lbl.config(text=f"{self.drops_zoom * 100:.0f}%")

    def _reset_zoom(self):
        self.drops_zoom = 1.0
        self.drops_pan = [0.0, 0.0]
        self._refresh_drops_image()
        self._update_zoom_label()

    def _apply_zoom(self, new_zoom, px, py):
        new_zoom = min(40.0, max(1.0, new_zoom))
        if new_zoom == self.drops_zoom:
            return
        cw = max(self.drops_canvas.winfo_width(), 1)
        ch = max(self.drops_canvas.winfo_height(), 1)
        cx = cw / 2 + self.drops_pan[0]
        cy = ch / 2 + self.drops_pan[1]
        ratio = new_zoom / self.drops_zoom
        self.drops_pan[0] = (cx + (cx - px) * (ratio - 1)) - cw / 2
        self.drops_pan[1] = (cy + (cy - py) * (ratio - 1)) - ch / 2
        self.drops_zoom = new_zoom
        self._refresh_drops_fast()
        self._update_zoom_label()

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
        factor = (1 / 1.1) if (getattr(event, "num", None) == 5
                               or getattr(event, "delta", 0) < 0) else 1.1
        self._apply_zoom(self.drops_zoom * factor, event.x, event.y)

    def _on_pan_start(self, event):
        self._pan_anchor = (event.x, event.y,
                            self.drops_pan[0], self.drops_pan[1])

    def _on_pan_move(self, event):
        if not self._pan_anchor or not self.result:
            return
        x0, y0, p0x, p0y = self._pan_anchor
        self.drops_pan[0] = p0x + (event.x - x0)
        self.drops_pan[1] = p0y + (event.y - y0)
        self._refresh_drops_fast()


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
