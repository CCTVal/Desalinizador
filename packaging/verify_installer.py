"""Comprueba el paquete gráfico y abre/cierra el instalador sin instalar nada."""
import ctypes
from ctypes import wintypes
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import time
import zipfile

from PyInstaller.archive.readers import CArchiveReader


ROOT = Path(__file__).resolve().parents[1]
WORK = Path(tempfile.mkdtemp(prefix="verificar_instalador_grafico_", dir=ROOT / "build"))
exe = ROOT / "dist/Instalar_DesalinizadorGotas.exe"
with zipfile.ZipFile(ROOT / "dist/DesalinizadorGotas_instalador.zip") as archive:
    assert archive.testzip() is None
    assert archive.read(exe.name) == exe.read_bytes()
    assert 'Instalar_DesalinizadorGotas.exe' in archive.read('instalar.bat').decode('ascii')
print("PASS: ZIP íntegro con instalador gráfico y lanzador correctos", flush=True)
packed = CArchiveReader(str(exe))
payload = next(name for name in packed.toc if name.replace('\\', '/') == 'payload/DesalinizadorGotas.exe')
original = (ROOT / 'dist/DesalinizadorGotas.exe').read_bytes()
assert hashlib.sha256(packed.extract(payload)).digest() == hashlib.sha256(original).digest()
assert any(name.replace('\\', '/') == 'payload/version.txt' for name in packed.toc)
assert any('cctval_logo.png' in name for name in packed.toc)
print("PASS: programa incluido coincide con el original; versión y logo presentes", flush=True)

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.EnumChildWindows.argtypes = [wintypes.HWND, callback_type, wintypes.LPARAM]
windows = []

@callback_type
def inspect_error(hwnd, _):
    text = ctypes.create_unicode_buffer(20000)
    user32.GetWindowTextW(hwnd, text, len(text))
    if text.value:
        print(text.value, flush=True)
    return True

@callback_type
def inspect(hwnd, _):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    handle = kernel32.OpenProcess(0x1000, False, pid.value)
    if handle:
        size = wintypes.DWORD(32768)
        path = ctypes.create_unicode_buffer(size.value)
        if kernel32.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(size)):
            if os.path.normcase(path.value) == os.path.normcase(str(exe)) and user32.IsWindowVisible(hwnd):
                title = ctypes.create_unicode_buffer(1024)
                user32.GetWindowTextW(hwnd, title, 1024)
                windows.append((hwnd, title.value))
        kernel32.CloseHandle(handle)
    return True

process = subprocess.Popen([str(exe)], cwd=WORK,
                           env=dict(os.environ, LOCALAPPDATA=str(WORK / 'localappdata')))
try:
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline and process.poll() is None:
        windows.clear()
        user32.EnumWindows(inspect, 0)
        if any('Instalador' in title or 'Unhandled exception' in title for _, title in windows):
            break
        time.sleep(.3)
    success = any('Instalador' in title and 'CCTVal' in title for _, title in windows)
    if not success:
        for hwnd, _ in windows:
            user32.EnumChildWindows(hwnd, inspect_error, 0)
    for hwnd, _ in windows:
        user32.PostMessageW(hwnd, 0x0010, 0, 0)
    process.wait(timeout=20)
    assert success, (process.returncode, windows)
    assert process.returncode == 0, process.returncode
    assert not (WORK / 'localappdata/Programs/DesalinizadorGotas').exists()
    print("PASS: ventana gráfica compilada abre y cierra sin errores ni instalación automática", flush=True)
finally:
    if process.poll() is None:
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True)
print('Evidencia: ' + str(WORK), flush=True)
