"""Pruebas del receptor sin abrir puertos físicos ni publicar lecturas de prueba."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.serial_receiver import SerialReceiver, MAX_LINE
import serial

VALID = b'{"lecturas":[{"pieza":103,"valor":12.5,"unidad":"bar"}]}'


class FakePort:
    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.closed = False

    @property
    def in_waiting(self):
        return 1

    def read(self, count):
        if self.chunks:
            return self.chunks.pop(0)
        raise serial.SerialException('Desconexión de prueba')

    def close(self):
        self.closed = True


class ReceiverTests(unittest.TestCase):
    def setUp(self):
        self.receiver = SerialReceiver()
        self.receiver.connection = object()  # Hardware ficticio, sin puerto del sistema.

    def test_freshness_partial_and_range(self):
        with patch('src.serial_receiver.time.monotonic', return_value=10):
            self.receiver.accept_line(VALID)
        with patch('src.serial_receiver.time.monotonic', return_value=12):
            rows = {r['pieza']: r for r in self.receiver.snapshot()['lecturas']}
            self.assertEqual(rows[103]['valor'], 12.5)
            self.assertEqual(rows[106]['estado'], 'esperando')
        with patch('src.serial_receiver.time.monotonic', return_value=16):
            rows = {r['pieza']: r for r in self.receiver.snapshot()['lecturas']}
            self.assertEqual(rows[103]['estado'], 'vencida')
            self.assertIsNone(rows[103]['valor'])
        self.receiver.accept_line(VALID.replace(b'12.5', b'150'))
        self.assertEqual(self.receiver.latest[103][0], 150)  # No recortar fuera de rango.

    def test_invalid_is_atomic(self):
        for message in [b'booting', b'{', b'\xff', VALID.replace(b'103', b'999'), VALID.replace(b'bar', b'psi'),
                        VALID.replace(b'12.5', b'NaN'), VALID.replace(b'12.5', b'true'), VALID.replace(b'12.5', b'"12.5"'),
                        b'{"lecturas":[{"pieza":103,"valor":1,"unidad":"bar"},{"pieza":103,"valor":2,"unidad":"bar"}]}',
                        b'{"lecturas":[{"pieza":103,"valor":1,"unidad":"bar"},{"pieza":120,"valor":20,"unidad":"bar"}]}',
                        b'x' * (MAX_LINE + 1)]:
            self.receiver.accept_line(message)
        self.assertFalse(self.receiver.latest)
        self.assertEqual(self.receiver.invalid_lines, 11)

    def test_fragmented_lines_and_recovery(self):
        port = FakePort([VALID[:10], VALID[10:] + b'\r\n', b'x' * (MAX_LINE + 1), b'garbage\n', VALID + b'\n'])
        self.receiver._read(port)
        self.assertEqual(self.receiver.valid_lines, 2)
        self.assertEqual(self.receiver.invalid_lines, 1)
        self.assertTrue(port.closed)
        self.assertIn('interrumpida', self.receiver.error)
        self.assertTrue(all(r['valor'] is None for r in self.receiver.snapshot()['lecturas']))

    def test_unlisted_port_rejected(self):
        with patch('src.serial_receiver.available_ports', return_value=[]), patch('src.serial_receiver.serial.Serial') as opened:
            with self.assertRaises(ValueError):
                self.receiver.connect('COM999', 115200)
            opened.assert_not_called()


if __name__ == '__main__':
    unittest.main()
