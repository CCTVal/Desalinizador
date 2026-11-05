"""Compila con las bibliotecas y DLL de Tcl/Tk del Python seleccionado."""
import os
from pathlib import Path
import subprocess
import sys
import argparse


ROOT = Path(__file__).resolve().parents[1]


def main(installer=False):
    env = os.environ.copy()
    # Las DLL de los Python basados en Conda están fuera de DLLs/.
    conda_bin = Path(sys.base_prefix) / "Library" / "bin"
    if conda_bin.is_dir():
        env["PATH"] = str(conda_bin) + os.pathsep + env.get("PATH", "")
    probe = subprocess.check_output(
        [sys.executable, "-c", "import tkinter as t; r=t.Tk(); "
         "print(r.tk.call('info','library')); "
         "print(r.tk.call('set','tk_library')); r.destroy()"],
        env=env, text=True,
    ).splitlines()
    tcl_data, tk_data = map(Path, probe)
    args = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
            "--onefile", "--windowed", "--name", "Instalar_DesalinizadorGotas" if installer else "DesalinizadorGotas",
            "--icon", "assets/cctval_icon.ico", "--add-data", "assets;assets",
            "--add-data", f"{tcl_data};_tcl_data",
            "--add-data", f"{tk_data};_tk_data"]
    if installer:
        args.extend(["--add-data", "dist/DesalinizadorGotas.exe;payload",
                     "--add-data", "build/installer_payload/version.txt;payload"])
        for module in ("numpy", "cv2", "matplotlib", "openpyxl"):
            args.extend(["--exclude-module", module])
    else:
        args.extend(["--hidden-import", "matplotlib.backends.backend_tkagg", "--collect-data", "matplotlib"])
    if conda_bin.is_dir():
        for pattern in ("tcl[89]*t.dll", "tk[89]*t.dll"):
            for dll in conda_bin.glob(pattern):
                args.extend(["--add-binary", f"{dll};."])
    for module in ("PyQt5", "PyQt6", "PySide2", "PySide6", "IPython",
                   "notebook", "sphinx", "vtk", "vtkmodules"):
        args.extend(["--exclude-module", module])
    args.append("installer_gui.py" if installer else "app.py")
    subprocess.run(args, cwd=ROOT, env=env, check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installer", action="store_true")
    main(parser.parse_args().installer)
