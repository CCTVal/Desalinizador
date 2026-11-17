"""Receive bounded JSON lines from Arduino. One process owns one serial port."""
import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import serial
from serial.tools import list_ports
from pydantic import BaseModel, ConfigDict, Field, model_validator

equipment = json.loads((Path(__file__).resolve().parents[1] / 'datos/equipos.json').read_text(encoding='utf-8'))
SENSORS = {
    part + 1: item['rango_declarado']
    for item in equipment['equipos'] if item['id'].startswith('sensor_')
    for part in item['piezas_cad_asociadas']
}
STALE_SECONDS = 5
MAX_LINE = 4096


class Reading(BaseModel):
    model_config = ConfigDict(extra='forbid')
    pieza: int = Field(strict=True)
    valor: float = Field(strict=True, allow_inf_nan=False)
    unidad: str

    @model_validator(mode='after')
    def known_sensor_and_unit(self):
        if self.pieza not in SENSORS or self.unidad != SENSORS[self.pieza]['unidad']:
            raise ValueError('Pieza o unidad desconocida')
        return self


class Packet(BaseModel):
    model_config = ConfigDict(extra='forbid')
    lecturas: list[Reading] = Field(min_length=1, max_length=4)

    @model_validator(mode='after')
    def unique_sensors(self):
        if len({item.pieza for item in self.lecturas}) != len(self.lecturas):
            raise ValueError('Pieza repetida')
        return self


class Connection(BaseModel):
    model_config = ConfigDict(extra='forbid')
    puerto: str = Field(min_length=1, max_length=128)
    baudios: Literal[9600, 19200, 38400, 57600, 115200] = 115200


def available_ports():
    return [{'puerto': p.device, 'descripcion': p.description} for p in list_ports.comports()]


class SerialReceiver:
    def __init__(self):
        self.lock = threading.Lock()
        self.lifecycle = threading.Lock()
        self.stop = threading.Event()
        self.thread = None
        self.connection = None
        self.port = None
        self.baud = None
        self.error = None
        self.latest = {}
        self.invalid_lines = 0
        self.valid_lines = 0

    def connect(self, port, baud):
        with self.lifecycle:
            if self.thread and self.thread.is_alive():
                raise ValueError('Desconecta el puerto actual antes de conectar otro.')
            if port not in {p['puerto'] for p in available_ports()}:
                raise ValueError('El puerto seleccionado ya no está disponible.')
            connection = serial.Serial(port, baud, timeout=.2)
            try:
                connection.reset_input_buffer()
            except Exception:
                connection.close()
                raise
            with self.lock:
                self.connection, self.port, self.baud = connection, port, baud
                self.error = None
                self.latest = {}
                self.valid_lines = self.invalid_lines = 0
            self.stop.clear()
            self.thread = threading.Thread(target=self._read, args=(connection,), daemon=True)
            self.thread.start()

    def disconnect(self):
        with self.lifecycle:
            self.stop.set()
            if self.thread:
                self.thread.join(timeout=2)
            # read() has a short timeout; keep the old worker isolated until it exits.
            if self.thread and self.thread.is_alive():
                raise RuntimeError('El puerto está terminando una lectura. Intenta desconectar otra vez.')
            with self.lock:
                self.connection = None

    def accept_line(self, line):
        try:
            if len(line) > MAX_LINE:
                raise ValueError('Línea demasiado larga')
            packet = Packet.model_validate_json(line)
        except ValueError:
            with self.lock:
                self.invalid_lines += 1
            return
        now, received = time.monotonic(), datetime.now(timezone.utc).isoformat()
        with self.lock:
            for item in packet.lecturas:
                self.latest[item.pieza] = (item.valor, now, received)
            self.valid_lines += 1

    def _read(self, connection):
        pending = bytearray()
        discard = False
        try:
            while not self.stop.is_set():
                chunk = connection.read(min(max(connection.in_waiting, 1), MAX_LINE))
                for byte in chunk:
                    if byte == 10:
                        if not discard and pending.strip():
                            self.accept_line(bytes(pending))
                        pending.clear()
                        discard = False
                    elif not discard:
                        pending.append(byte)
                        if len(pending) > MAX_LINE:
                            pending.clear()
                            discard = True
                            with self.lock:
                                self.invalid_lines += 1
        except (serial.SerialException, OSError) as exc:
            with self.lock:
                self.error = f'Conexión serie interrumpida: {exc}'
        finally:
            try:
                connection.close()
            finally:
                with self.lock:
                    self.connection = None

    def snapshot(self):
        now = time.monotonic()
        with self.lock:
            connected = self.connection is not None and not self.stop.is_set()
            rows = []
            for part, limits in SENSORS.items():
                sample = self.latest.get(part)
                age = max(0, now - sample[1]) if sample else None
                state = 'desconectado' if not connected else 'esperando' if sample is None else 'vencida' if age > STALE_SECONDS else 'vigente'
                rows.append({'pieza': part, 'unidad': limits['unidad'], 'valor': sample[0] if sample and state == 'vigente' else None,
                             'estado': state, 'recibida_en': sample[2] if sample else None, 'edad_s': age})
            return {'conectado': connected, 'puerto': self.port, 'baudios': self.baud, 'error': self.error,
                    'mensajes_validos': self.valid_lines, 'mensajes_invalidos': self.invalid_lines,
                    'caducidad_s': STALE_SECONDS, 'lecturas': rows}
