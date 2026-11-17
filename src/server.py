"""Backend local: API de estado y visor CAD construido con Vite."""
from pathlib import Path
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from .serial_receiver import SerialReceiver, Connection, available_ports
import serial

ROOT = Path(__file__).resolve().parents[1]
receiver = SerialReceiver()


@asynccontextmanager
async def lifespan(app):
    yield
    receiver.disconnect()


app = FastAPI(title="Gemelo digital de planta", version="0.1.0", lifespan=lifespan)


def require_local(request):
    if not request.client or request.client.host not in {'127.0.0.1', '::1'} or request.url.hostname not in {'localhost', '127.0.0.1', '::1'}:
        raise HTTPException(403, 'La conexión serie se controla desde este computador.')
    origin = request.headers.get('origin')
    if origin and urlsplit(origin).netloc != request.url.netloc:
        raise HTTPException(403, 'Origen no permitido.')


@app.get('/api/serie/puertos')
def ports(request: Request):
    require_local(request)
    return available_ports()


@app.post('/api/serie/conectar')
def connect(connection: Connection, request: Request):
    require_local(request)
    try:
        receiver.connect(connection.puerto, connection.baudios)
    except (ValueError, serial.SerialException, OSError) as exc:
        raise HTTPException(409, str(exc)) from exc
    return receiver.snapshot()


@app.post('/api/serie/desconectar')
def disconnect(request: Request):
    require_local(request)
    try:
        receiver.disconnect()
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    return receiver.snapshot()


@app.get('/api/lecturas')
def readings(response: Response):
    response.headers['Cache-Control'] = 'no-store'
    return receiver.snapshot()


@app.get("/api/estado")
def estado():
    return {
        "estado": "simulacion_bomba",
        "modelo": "P23.00-00-A008v2.stp",
        "sensores_conectados": any(row['estado'] == 'vigente' for row in receiver.snapshot()['lecturas']),
        "puerto_serie_conectado": receiver.snapshot()['conectado'],
        "simulacion_agua": True,
        "simulacion_calibrada": False,
        "calculo": "navegador: curva WDM y circuito supuesto",
    }


if (ROOT / "dist").is_dir():
    app.mount("/", StaticFiles(directory=ROOT / "dist", html=True), name="visor")
