"""Instalador gráfico de Análisis de tamaño de gota CCTVal (Windows)."""
import ctypes
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageDraw, ImageTk


ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
APP_NAME = "DesalinizadorGotas.exe"
PRIMARY = "#2e31c6"
ACCENT = "#0074ff"
INK = "#33373f"
MUTED = "#626a7a"
WHITE = "#ffffff"


def known_folder(identifier):
    buffer = ctypes.create_unicode_buffer(32768)
    result = ctypes.windll.shell32.SHGetFolderPathW(None, identifier, None, 0, buffer)
    if result != 0 or not buffer.value:
        raise OSError("No se pudo localizar el escritorio o el menú Inicio de Windows.")
    return Path(buffer.value)


class Installation:
    def __init__(self, payload=None, destination=None, shortcut_dirs=None, location_file=None):
        self.payload = Path(payload) if payload is not None else ROOT / "payload"
        self.location_file = (Path(location_file) if location_file is not None else
                              Path(os.environ["LOCALAPPDATA"]) / "CCTVal" / "Gotas" / "installation.json"
                              if destination is None else None)
        self.destination = Path(destination) if destination is not None else self.saved_destination()
        self.shortcut_dirs = (list(map(Path, shortcut_dirs)) if shortcut_dirs is not None
                              else [known_folder(0x10), known_folder(0x02)])

    def saved_destination(self):
        if self.location_file is not None:
            try:
                value = json.loads(self.location_file.read_text(encoding="utf-8"))["directory"]
                if isinstance(value, str) and value and Path(value).is_absolute():
                    return Path(value)
            except (OSError, ValueError, KeyError, TypeError):
                pass
        return Path(os.environ["LOCALAPPDATA"]) / "Programs" / "DesalinizadorGotas"

    def remember_destination(self):
        if self.location_file is not None:
            self.location_file.parent.mkdir(parents=True, exist_ok=True)
            self.location_file.write_text(json.dumps({"directory": str(self.destination)}, ensure_ascii=False),
                                          encoding="utf-8")

    @property
    def executable(self):
        return self.destination / APP_NAME

    @property
    def installed(self):
        return self.executable.is_file()

    def version(self, installed=False):
        folder = self.destination if installed else self.payload
        path = folder / "version.txt"
        return path.read_text(encoding="utf-8-sig").strip() if path.is_file() else "Sin información"

    def install(self, update=False):
        if update and not self.installed:
            raise ValueError("Primero instala el programa con el botón Instalar.")
        if not update and self.installed:
            raise ValueError("El programa ya está instalado. Usa el botón Actualizar.")
        source = self.payload / APP_NAME
        if not source.is_file():
            raise FileNotFoundError("Faltan los archivos del programa. Descarga de nuevo el instalador completo.")
        self.destination.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix="gotas_", suffix=".nuevo", dir=self.destination)
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            shutil.copy2(source, temporary)
            # Reemplazo atómico: un fallo conserva la versión instalada.
            os.replace(temporary, self.executable)
        except PermissionError as exc:
            raise OSError("Cierra Análisis de gotas y comprueba que puedes escribir en la carpeta elegida. No se pudo reemplazar el programa.") from exc
        finally:
            temporary.unlink(missing_ok=True)
        version_temp = self.destination / "version.txt.nuevo"
        version_temp.write_text(self.version() + "\n", encoding="utf-8")
        os.replace(version_temp, self.destination / "version.txt")
        warnings = []
        try:
            self.remember_destination()
        except OSError:
            warnings.append("El programa quedó instalado. Vuelve a elegir esta carpeta la próxima vez: no se pudo guardar la ubicación.")
        try:
            self.shortcuts()
        except (OSError, subprocess.SubprocessError) as exc:
            warnings.append("El programa quedó instalado, pero no se pudieron crear los accesos directos. " + str(exc))
        return "\n".join(warnings)

    def shortcuts(self, remove=False):
        env = dict(os.environ, CCTVAL_INSTALL_EXE=str(self.executable),
                   CCTVAL_SHORTCUT_DIRS="\n".join(map(str, self.shortcut_dirs)))
        script = "$ErrorActionPreference='Stop'; $shell=New-Object -ComObject WScript.Shell; "
        script += "foreach ($dir in ($env:CCTVAL_SHORTCUT_DIRS -split [char]10)) { "
        script += "$path=Join-Path $dir 'Analisis de gotas CCTVal.lnk'; "
        if remove:
            script += ("if (Test-Path -LiteralPath $path) { $lnk=$shell.CreateShortcut($path); "
                       "if ($lnk.TargetPath -eq $env:CCTVAL_INSTALL_EXE) {Remove-Item -LiteralPath $path -Force} }")
        else:
            script += ("$null=New-Item -ItemType Directory -Path $dir -Force; "
                       "$lnk=$shell.CreateShortcut($path); $lnk.TargetPath=$env:CCTVAL_INSTALL_EXE; "
                       "$lnk.WorkingDirectory=Split-Path $env:CCTVAL_INSTALL_EXE; "
                       "$lnk.IconLocation=$env:CCTVAL_INSTALL_EXE; $lnk.Save()")
        script += " }"
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            env=env, capture_output=True, text=True, errors="replace", timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode:
            raise OSError("Comprueba los permisos del escritorio y del menú Inicio.")

    def uninstall(self):
        if not self.installed:
            raise ValueError("El programa no está instalado.")
        try:
            self.executable.unlink()
        except PermissionError as exc:
            raise OSError("Cierra Análisis de gotas y vuelve a intentar la desinstalación.") from exc
        (self.destination / "version.txt").unlink(missing_ok=True)
        self.shortcuts(remove=True)
        # Conservar cualquier archivo personal que el usuario haya guardado aquí.
        if not any(self.destination.iterdir()):
            self.destination.rmdir()

    def open_program(self):
        env = dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT="1")
        subprocess.Popen([str(self.executable)], cwd=self.destination, env=env)


class Installer(tk.Tk):
    def __init__(self, installation=None):
        super().__init__()
        self.service = installation or Installation()
        self.busy = False
        self.events = queue.Queue()
        self.title("Instalador · Análisis de gotas CCTVal")
        self.geometry("760x700")
        self.minsize(720, 680)
        self.configure(bg=PRIMARY)
        self.protocol("WM_DELETE_WINDOW", self.close)
        if sys.platform == "win32":
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("CCTVal.Gotas.Instalador")
        self.iconbitmap(default=str(ROOT / "assets/cctval_icon.ico"))
        logo = Image.open(ROOT / "assets/cctval_logo.png").convert("RGBA")
        logo.thumbnail((300, 110), Image.Resampling.LANCZOS)
        self.logo = ImageTk.PhotoImage(logo)
        self.canvas = tk.Canvas(self, bd=0, highlightthickness=0, bg=PRIMARY)
        self.canvas.pack(fill="both", expand=True)
        self.card = tk.Frame(self.canvas, bg=WHITE)
        self.heading = self.label(self.card, "", size=21, bold=True, color=PRIMARY)
        self.heading.pack(anchor="w")
        self.label(self.card, "Análisis de tamaño de gota · Desalinizador", size=11).pack(anchor="w", pady=(4, 8))
        self.state_label = self.label(self.card, "", size=11, bold=True, color=PRIMARY)
        self.state_label.pack(anchor="w")
        self.versions = self.label(self.card, "", size=10, color=MUTED, justify="left")
        self.versions.pack(anchor="w", pady=(4, 8))
        self.label(self.card, "Carpeta de instalación o actualización", size=10, bold=True).pack(anchor="w")
        path_row = tk.Frame(self.card, bg=WHITE)
        path_row.pack(fill="x", pady=(4, 4))
        self.choose_button = self.button(path_row, "Elegir carpeta…", self.choose_destination, secondary=True)
        self.choose_button.configure(font=("Segoe UI", 10, "bold"), pady=8, padx=12)
        self.choose_button.pack(side="right", padx=(8, 0))
        self.path_var = tk.StringVar(value=str(self.service.destination))
        self.path_entry = tk.Entry(path_row, textvariable=self.path_var, state="readonly", font=("Segoe UI", 10),
                                   readonlybackground="#f3f5fc", fg=INK, relief="solid", bd=1)
        self.path_entry.pack(side="left", fill="x", expand=True, ipady=8)
        self.path_hint = self.label(self.card, "Para actualizar, selecciona la carpeta del programa.",
                                   size=9, color=MUTED, justify="left", wraplength=570)
        self.path_hint.pack(anchor="w", pady=(0, 10))
        actions = tk.Frame(self.card, bg=WHITE)
        actions.pack(fill="x")
        actions.columnconfigure((0, 1), weight=1, uniform="action")
        self.install_button = self.button(actions, "Instalar programa", lambda: self.start("install"))
        self.install_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.update_button = self.button(actions, "Actualizar programa", lambda: self.start("update"))
        self.update_button.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("CCTVal.Horizontal.TProgressbar", troughcolor="#eef0fa", background=ACCENT,
                        borderwidth=0, lightcolor=ACCENT, darkcolor=ACCENT)
        self.progress = ttk.Progressbar(self.card, mode="determinate", style="CCTVal.Horizontal.TProgressbar")
        self.progress.pack(fill="x", pady=(14, 6))
        self.status = self.label(self.card, "Elige una opción para continuar.", size=10, color=MUTED,
                                 wraplength=570, justify="left")
        self.status.pack(anchor="w")
        footer = tk.Frame(self.card, bg=WHITE)
        footer.pack(side="bottom", fill="x", pady=(10, 0), before=self.heading)
        self.uninstall_button = self.button(footer, "Desinstalar", lambda: self.start("uninstall"), secondary=True)
        self.uninstall_button.pack(side="left")
        self.exit_button = self.button(footer, "Salir", self.close, secondary=True)
        self.exit_button.pack(side="right")
        self.open_button = self.button(footer, "Abrir programa", self.open_program, secondary=True)
        self.open_button.pack(side="right", padx=8)
        self.canvas.bind("<Configure>", self.draw)
        self.refresh()
        self.after(100, self.poll)

    @staticmethod
    def label(parent, text, size=11, bold=False, color=INK, **kwargs):
        return tk.Label(parent, text=text, font=("Segoe UI", size, "bold" if bold else "normal"),
                        bg=WHITE, fg=color, **kwargs)

    @staticmethod
    def button(parent, text, command, secondary=False):
        return tk.Button(parent, text=text, command=command, font=("Segoe UI", 11, "bold"),
                         bg="#eef0fa" if secondary else PRIMARY, fg=PRIMARY if secondary else WHITE,
                         activebackground="#dde2fc" if secondary else "#24268f",
                         activeforeground=PRIMARY if secondary else WHITE, disabledforeground="#747c8d",
                         relief="flat", bd=0, padx=16, pady=12, cursor="hand2", takefocus=True,
                         highlightthickness=2, highlightbackground=WHITE, highlightcolor=ACCENT)

    def draw(self, event):
        w, h = event.width, event.height
        image = Image.new("RGB", (w, h))
        painter = ImageDraw.Draw(image)
        for y in range(h):
            t = y / max(h - 1, 1)
            color = tuple(round(a + (b - a) * t) for a, b in zip((0, 116, 255), (46, 49, 198)))
            painter.line((0, y, w, y), fill=color)
        painter.rounded_rectangle((30, 130, w - 30, h - 58), radius=26, fill=WHITE)
        self.background = ImageTk.PhotoImage(image)
        self.canvas.delete("decoration")
        self.canvas.create_image(0, 0, image=self.background, anchor="nw", tags="decoration")
        self.canvas.create_image(w // 2, 65, image=self.logo, tags="decoration")
        self.card.place(x=58, y=154, width=w - 116, height=h - 234)
        self.path_hint.configure(wraplength=w - 130)
        self.status.configure(wraplength=w - 130)

    def refresh(self):
        installed = self.service.installed
        self.heading.configure(text="Tu programa está instalado" if installed else "Instala Análisis de gotas")
        self.state_label.configure(text="Listo para actualizar" if installed else "Listo para instalar")
        version = "Versión disponible: " + self.service.version()
        if installed:
            version += "\nVersión instalada: " + self.service.version(installed=True)
        self.versions.configure(text=version)
        self.install_button.configure(state="disabled" if installed or self.busy else "normal")
        self.update_button.configure(state="normal" if installed and not self.busy else "disabled")
        for button in (self.uninstall_button, self.open_button):
            button.configure(state="normal" if installed and not self.busy else "disabled")
        self.exit_button.configure(state="disabled" if self.busy else "normal")
        self.choose_button.configure(state="disabled" if self.busy else "normal")

    def choose_destination(self):
        if self.busy:
            return
        folder = filedialog.askdirectory(parent=self, title="Elegir carpeta para instalar o actualizar",
                                          initialdir=str(self.service.destination if self.service.destination.is_dir()
                                                         else self.service.destination.parent), mustexist=False)
        if not folder:
            return
        self.service.destination = Path(folder).resolve()
        self.path_var.set(str(self.service.destination))
        self.refresh()
        self.progress.configure(value=0)
        self.status.configure(text="Programa encontrado. Puedes actualizarlo en esta carpeta."
                              if self.service.installed else "El programa se instalará en la carpeta elegida.", fg=PRIMARY)

    def start(self, action):
        if self.busy:
            return
        if action == "uninstall" and not messagebox.askyesno(
                "Desinstalar programa", "¿Quieres desinstalar Análisis de gotas?\nTus imágenes y resultados se conservarán.", parent=self):
            return
        self.busy = True
        self.refresh()
        self.progress.configure(mode="indeterminate", value=0)
        self.progress.start(12)
        self.status.configure(text={"install": "Instalando el programa…", "update": "Actualizando el programa…",
                                    "uninstall": "Desinstalando el programa…"}[action], fg=PRIMARY)
        def work():
            try:
                warning = self.service.uninstall() if action == "uninstall" else self.service.install(update=action == "update")
                self.events.put((action, warning, None))
            except Exception as exc:
                self.events.put((action, None, str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        try:
            action, warning, error = self.events.get_nowait()
        except queue.Empty:
            pass
        else:
            self.busy = False
            self.progress.stop()
            self.progress.configure(mode="determinate", value=0 if error else 100)
            self.refresh()
            if error:
                self.status.configure(text=error, fg="#a1263a")
                messagebox.showerror("No se pudo completar", error, parent=self)
            else:
                message = {"install": "Instalación completada. Ya puedes abrir el programa.",
                           "update": "Actualización completada. Ya puedes abrir el programa.",
                           "uninstall": "Programa desinstalado."}[action]
                self.status.configure(text=warning or message, fg=PRIMARY)
                if warning:
                    messagebox.showwarning("Accesos directos", warning, parent=self)
        self.after(100, self.poll)

    def open_program(self):
        try:
            self.service.open_program()
        except OSError as exc:
            messagebox.showerror("No se pudo abrir", str(exc), parent=self)

    def close(self):
        if self.busy:
            messagebox.showinfo("Operación en curso", "Espera a que termine la operación antes de cerrar.", parent=self)
        else:
            self.destroy()


if __name__ == "__main__":
    Installer().mainloop()
