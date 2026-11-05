"""Prueba la interfaz y las operaciones del instalador en carpetas aisladas."""
from pathlib import Path
import shutil
import tempfile
import time
from unittest import mock

from PIL import ImageGrab

import installer_gui as gui


ROOT = Path(__file__).resolve().parent
WORK = Path(tempfile.mkdtemp(prefix="qa_instalador_grafico_", dir=ROOT / "build"))
PAYLOAD = WORK / "payload"
PAYLOAD.mkdir()
shutil.copy2(ROOT / "dist" / gui.APP_NAME, PAYLOAD / gui.APP_NAME)
(PAYLOAD / "version.txt").write_text("versión de prueba 1", encoding="utf-8")
service = gui.Installation(PAYLOAD, WORK / "programa", [WORK / "escritorio", WORK / "inicio"],
                           location_file=WORK / "config" / "installation.json")


def pump(window, until=lambda: True):
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        window.update()
        if until():
            return
        time.sleep(.03)
    raise AssertionError("La operación no terminó a tiempo")


def capture(window, name):
    window.lift()
    window.update()
    time.sleep(.2)
    from ctypes import wintypes
    user32 = gui.ctypes.windll.user32
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    hwnd = user32.GetAncestor(window.winfo_id(), 2)
    ImageGrab.grab(window=hwnd).save(ROOT / 'build' / ('instalador_' + name))


window = gui.Installer(service)
errors = []
try:
    with mock.patch.object(gui.messagebox, "showerror", side_effect=lambda *a, **k: errors.append(a)), \
         mock.patch.object(gui.messagebox, "showwarning", side_effect=lambda *a, **k: errors.append(a)):
        pump(window)
        assert str(window.install_button['state']) == 'normal'
        assert str(window.update_button['state']) == 'disabled'
        assert str(window.open_button['state']) == 'disabled'
        capture(window, "01_sin_instalar.png")
        print("PASS: logo, ventana inicial y estado de botones", flush=True)

        chosen = WORK / "Carpeta elegida con espacios" / "Gotas"
        chosen.mkdir(parents=True)
        with mock.patch.object(gui.filedialog, 'askdirectory', return_value=str(chosen)):
            window.choose_button.invoke()
        assert service.destination == chosen
        assert window.path_var.get() == str(chosen)
        assert str(window.install_button['state']) == 'normal'
        with mock.patch.object(gui.filedialog, 'askdirectory', return_value=''):
            window.choose_button.invoke()
        assert service.destination == chosen
        print("PASS: elegir carpeta personalizada y cancelar el selector", flush=True)

        window.install_button.invoke()
        assert window.busy
        assert str(window.exit_button['state']) == 'disabled'
        assert str(window.choose_button['state']) == 'disabled'
        pump(window, lambda: not window.busy)
        assert not errors, errors
        assert service.executable.read_bytes() == (PAYLOAD / gui.APP_NAME).read_bytes()
        assert str(window.install_button['state']) == 'disabled'
        assert str(window.update_button['state']) == 'normal'
        assert str(window.open_button['state']) == 'normal'
        for folder in service.shortcut_dirs:
            assert (folder / 'Analisis de gotas CCTVal.lnk').is_file()
        capture(window, "02_instalado.png")
        print("PASS: instalar desde el botón, progreso y accesos directos reales", flush=True)
        remembered = gui.Installation(PAYLOAD, shortcut_dirs=service.shortcut_dirs, location_file=service.location_file)
        assert remembered.destination == chosen and remembered.installed
        empty = WORK / "otra carpeta"
        empty.mkdir()
        with mock.patch.object(gui.filedialog, 'askdirectory', return_value=str(empty)):
            window.choose_button.invoke()
        assert str(window.update_button['state']) == 'disabled'
        with mock.patch.object(gui.filedialog, 'askdirectory', return_value=str(chosen)):
            window.choose_button.invoke()
        assert str(window.update_button['state']) == 'normal'
        print("PASS: recordar la ubicación y detectar una instalación al elegir su carpeta", flush=True)

        # La copia preparada no reemplaza al ejecutable instalado si Windows la rechaza.
        previous = service.executable.read_bytes()
        with mock.patch.object(gui.os, "replace", side_effect=PermissionError("programa abierto")):
            try:
                service.install(update=True)
                raise AssertionError("Se esperaba un fallo de reemplazo")
            except OSError as exc:
                assert "Cierra" in str(exc)
        assert service.executable.read_bytes() == previous
        assert not list(service.destination.glob('*.nuevo'))
        print("PASS: un reemplazo fallido conserva la versión instalada", flush=True)

        (PAYLOAD / "version.txt").write_text("versión de prueba 2", encoding="utf-8")
        window.update_button.invoke()
        pump(window, lambda: not window.busy)
        assert not errors, errors
        assert service.version(installed=True) == "versión de prueba 2"
        with mock.patch.object(service, "open_program") as launch:
            window.open_button.invoke()
            launch.assert_called_once()
        print("PASS: actualizar y botón Abrir programa", flush=True)

        window.geometry("720x680")
        pump(window)
        window.update_idletasks()
        assert window.status.winfo_height() >= 15
        assert window.status.winfo_y() + window.status.winfo_height() <= window.uninstall_button.master.winfo_y()
        assert window.uninstall_button.winfo_height() >= 40
        capture(window, "03_tamano_minimo.png")
        print("PASS: controles visibles en el tamaño mínimo", flush=True)

        with mock.patch.object(gui.messagebox, "askyesno", return_value=False):
            window.uninstall_button.invoke()
        assert service.installed
        personal = service.destination / 'resultado_personal.txt'
        personal.write_text('conservar', encoding='utf-8')
        with mock.patch.object(gui.messagebox, "askyesno", return_value=True):
            window.uninstall_button.invoke()
        pump(window, lambda: not window.busy)
        assert not errors, errors
        assert not service.installed
        assert personal.read_text(encoding='utf-8') == 'conservar'
        assert all(not list(folder.glob('*.lnk')) for folder in service.shortcut_dirs)
        assert str(window.install_button['state']) == 'normal'
        print("PASS: cancelar desinstalación y desinstalar conservando archivos personales", flush=True)
finally:
    window.destroy()
print("Evidencia: " + str(WORK), flush=True)
