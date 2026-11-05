"""Convierte un CSV de colocación de componentes de seis a siete columnas.

Ejecuta ``python convertir_pnp.py`` para elegir los archivos en una ventana.
"""

import argparse
import csv
from pathlib import Path


ORIGEN = ["Designator", "Mid X", "Mid Y", "Rotation", "Value", "Footprint"]
DESTINO = [
    "Designator", "Footprint", "Mid X", "Mid Y", "Rotation", "Comment/Value", "Layer"
]
ARCHIVO_EJEMPLO = "PnP_Muon Amplifier Board v2.0 v4_front.csv"


def convertir(entrada: Path, salida: Path, layer: str) -> int:
    if entrada.resolve() == salida.resolve():
        raise ValueError("El archivo de salida debe ser distinto del archivo original.")

    with entrada.open("r", encoding="utf-8-sig", newline="") as archivo:
        filas = list(csv.reader(archivo))

    if filas and filas[0] == ORIGEN:
        filas = filas[1:]

    for numero, fila in enumerate(filas, start=1):
        if len(fila) != len(ORIGEN):
            raise ValueError(f"Fila de datos {numero}: se esperaban 6 columnas y hay {len(fila)}.")

    with salida.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(DESTINO)
        for designator, mid_x, mid_y, rotation, value, footprint in filas:
            escritor.writerow([designator, footprint, mid_x, mid_y, rotation, value, layer])

    return len(filas)


def abrir_ventana(layer: str = "Top") -> None:
    """Permite elegir el CSV de entrada y la ruta de salida con PyQt6."""
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import (
        QApplication, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
        QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget,
    )

    aplicacion = QApplication.instance() or QApplication([])
    ventana = QWidget()
    ventana.setWindowTitle("Conversor de archivos de componentes")
    ventana.setObjectName("ventana")
    ventana.setMinimumSize(600, 300)
    ventana.resize(720, 330)
    icono = Path(__file__).resolve().parent / "assets" / "cctval_icon.png"
    ventana.setWindowIcon(QIcon(str(icono)))
    ventana.setStyleSheet("""
        QWidget#ventana { background-color: #f3f5fc; color: #23264a; font: 10pt 'Segoe UI'; }
        QFrame#tarjeta { background-color: white; border: 1px solid #dce2f2;
                         border-radius: 16px; }
        QLabel#etiqueta { color: #2e31c6; font-weight: bold; }
        QLabel#estado { color: #2e31c6; }
        QLineEdit, QComboBox { background-color: #f8faff; border: 1px solid #cbd5ea;
                              border-radius: 8px; padding: 9px; min-height: 20px; }
        QLineEdit:focus, QComboBox:focus { border: 2px solid #0074ff; }
        QPushButton { border-radius: 8px; padding: 10px 16px; font-weight: bold; }
        QPushButton#principal { background-color: #0074ff; color: white; border: none; }
        QPushButton#principal:hover { background-color: #2e31c6; }
        QPushButton#secundario { background-color: white; color: #2e31c6;
                                 border: 1px solid #2e31c6; }
        QPushButton#secundario:hover { background-color: #eef0ff; }
        QPushButton#principal:disabled, QPushButton#secundario:disabled {
            background-color: #e5e9f3; color: #8891a7; border: 1px solid #e5e9f3;
        }
    """)

    disposicion = QVBoxLayout(ventana)
    disposicion.setContentsMargins(18, 18, 18, 18)

    tarjeta = QFrame()
    tarjeta.setObjectName("tarjeta")
    contenido = QVBoxLayout(tarjeta)
    contenido.setContentsMargins(24, 22, 24, 22)
    contenido.setSpacing(10)
    disposicion.addWidget(tarjeta)

    entrada = QLineEdit()
    entrada.setReadOnly(True)
    salida = QLineEdit()
    salida.setReadOnly(True)
    capa = QComboBox()
    capa.addItem("Cara superior", "Top")
    capa.addItem("Cara inferior", "Bottom")
    indice_capa = capa.findData(layer)
    if indice_capa < 0:
        capa.addItem(layer, layer)
        indice_capa = capa.count() - 1
    capa.setCurrentIndex(indice_capa)
    estado = QLabel("Selecciona el archivo CSV de origen.")
    estado.setWordWrap(True)

    etiqueta_entrada = QLabel("1. Archivo de entrada")
    etiqueta_entrada.setObjectName("etiqueta")
    contenido.addWidget(etiqueta_entrada)
    fila_entrada = QHBoxLayout()
    fila_entrada.addWidget(entrada)
    boton_entrada = QPushButton("Elegir archivo…")
    boton_entrada.setObjectName("secundario")
    fila_entrada.addWidget(boton_entrada)
    contenido.addLayout(fila_entrada)

    etiqueta_salida = QLabel("2. Guardar archivo convertido en")
    etiqueta_salida.setObjectName("etiqueta")
    contenido.addWidget(etiqueta_salida)
    fila_salida = QHBoxLayout()
    fila_salida.addWidget(salida)
    boton_salida = QPushButton("Elegir destino…")
    boton_salida.setObjectName("secundario")
    boton_salida.setEnabled(False)
    fila_salida.addWidget(boton_salida)
    contenido.addLayout(fila_salida)

    fila_final = QHBoxLayout()
    etiqueta_capa = QLabel("Cara de la placa:")
    etiqueta_capa.setObjectName("etiqueta")
    fila_final.addWidget(etiqueta_capa)
    fila_final.addWidget(capa)
    fila_final.addStretch()
    boton_convertir = QPushButton("Convertir")
    boton_convertir.setObjectName("principal")
    boton_convertir.setEnabled(False)
    fila_final.addWidget(boton_convertir)
    contenido.addLayout(fila_final)
    estado.setObjectName("estado")
    contenido.addWidget(estado)

    def elegir_salida() -> None:
        archivo_entrada = Path(entrada.text())
        sugerencia = archivo_entrada.with_name(f"{archivo_entrada.stem}_convertido.csv")
        ruta, _ = QFileDialog.getSaveFileName(
            ventana, "Guardar CSV convertido", str(sugerencia),
            "Archivos CSV (*.csv);;Todos los archivos (*)",
        )
        if ruta:
            if not Path(ruta).suffix:
                ruta += ".csv"
            salida.setText(ruta)
            boton_convertir.setEnabled(True)
            estado.setText("Archivos listos. Pulsa «Convertir».")

    def elegir_entrada() -> None:
        ruta, _ = QFileDialog.getOpenFileName(
            ventana, "Seleccionar archivo CSV de origen", "",
            "Archivos CSV (*.csv);;Todos los archivos (*)",
        )
        if ruta:
            entrada.setText(ruta)
            salida.clear()
            boton_convertir.setEnabled(False)
            boton_salida.setEnabled(True)
            estado.setText("Elige dónde guardar el CSV convertido.")
            elegir_salida()

    def ejecutar_conversion() -> None:
        try:
            cantidad = convertir(Path(entrada.text()), Path(salida.text()), capa.currentData())
        except (OSError, UnicodeError, ValueError, csv.Error) as error:
            QMessageBox.critical(ventana, "No se pudo convertir", str(error))
            estado.setText("No se pudo convertir el archivo.")
            return
        estado.setText(f"Convertidas {cantidad} filas: {salida.text()}")
        QMessageBox.information(
            ventana, "Conversión terminada",
            f"Convertidas {cantidad} filas.\n\nArchivo guardado en:\n{salida.text()}",
        )

    boton_entrada.clicked.connect(elegir_entrada)
    boton_salida.clicked.connect(elegir_salida)
    boton_convertir.clicked.connect(ejecutar_conversion)
    ventana.show()
    aplicacion.exec()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "entrada", type=Path, nargs="?",
        help=f"CSV original (por defecto: Descargas/{ARCHIVO_EJEMPLO})",
    )
    parser.add_argument("salida", type=Path, nargs="?", help="CSV convertido (por defecto: Escritorio)")
    parser.add_argument("--layer", default="Top", help="Cara de la placa en el CSV (por defecto: superior)")
    parser.add_argument("--cli", action="store_true", help="Usar la línea de comandos sin abrir la ventana")
    args = parser.parse_args()

    if not (args.cli or args.entrada or args.salida):
        abrir_ventana(args.layer)
        return

    entrada = args.entrada or Path.home() / "Downloads" / ARCHIVO_EJEMPLO
    salida = args.salida or Path.home() / "Desktop" / f"{entrada.stem}_convertido.csv"
    cantidad = convertir(entrada, salida, args.layer)
    print(f"Convertidas {cantidad} filas: {salida}")


if __name__ == "__main__":
    main()
