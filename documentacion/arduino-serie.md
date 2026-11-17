# Recepción del Arduino por puerto serie

La aplicación puede recibir lecturas desde un Arduino conectado por USB al mismo computador. FastAPI mantiene un receptor pySerial; el navegador consulta las últimas lecturas cada segundo. Es actualización periódica para visualización, sin garantía de tiempo real determinista. No se envían comandos de actuación ni se escribe al puerto desde el backend.

## Conexión

1. Instala las dependencias de `requirements.txt` en `.venv` y construye el frontend con `npm.cmd run build`.
2. Inicia un solo proceso: `./.venv/Scripts/python.exe -m uvicorn src.server:app --host 127.0.0.1 --port 8001`.
3. Conecta el Arduino por USB y cierra el monitor/plotter serie del IDE para liberar el puerto.
4. En **Sensores**, abre **Conexión Arduino**, busca puertos y selecciona el COM de la placa y la misma velocidad configurada en su programa (115200 por defecto).
5. Pulsa **Conectar**. Se selecciona el origen **Arduino por serie**. Algunas placas reinician al abrir el puerto; espera a que comience su programa.

No se conecta automáticamente ni se elige un puerto por su apariencia. Abrir otra pestaña comparte la conexión del backend; desconectar desde una pestaña la cierra para todas. Cerrar solo el navegador deja al receptor activo hasta desconectar o detener el servidor. No uses múltiples workers: la conexión y los últimos valores se mantienen en memoria en un solo proceso. Reiniciar el servidor borra los valores.

## Mensaje del Arduino

Una línea JSON por adquisición, terminada en salto de línea (`Serial.println`). Debe contener entre una y cuatro lecturas. Cada pieza aparece una sola vez. Usa números de pieza del visor, no IDs internos ni números de canal ADC.

| Pieza | Magnitud | Unidad exacta | Rango declarado |
| --- | --- | --- | --- |
| 103 | Presión Volltell EPT1000 | `bar` | 0–100 |
| 106 | Presión Volltell EPT1000 | `bar` | 0–100 |
| 136 | Caudal de agua | `L/min` | 10–100 |
| 120 | Temperatura PT100 | `°C` | −50 a 250 |

Ejemplo **ficticio de formato**, no lecturas de planta:

```json
{"lecturas":[{"pieza":103,"valor":8.12,"unidad":"bar"},{"pieza":106,"valor":7.85,"unidad":"bar"},{"pieza":136,"valor":25.4,"unidad":"L/min"},{"pieza":120,"valor":21.6,"unidad":"\u00b0C"}]}
```

El escape `\u00b0C` equivale a `°C`. No envíes números como texto. Se rechazan NaN, infinito, unidades diferentes, piezas desconocidas, piezas repetidas, campos inesperados o más de 4096 bytes por línea. Un paquete inválido se descarta completo y aumenta el contador de mensajes descartados. Las líneas fragmentadas durante la lectura se reconstruyen hasta el salto de línea. Un dato fuera del rango declarado se conserva con aviso; no se recorta.

`arduino/EnviarSensores.h` contiene la función completa `enviarSensores(salida, p103Bar, p106Bar, q136LMin, t120C)`, que genera ese formato sin bibliotecas JSON adicionales. Inclúyela en tu programa y pásale los valores ya convertidos a las unidades indicadas; `NAN` omite un sensor con adquisición inválida. El programa debe configurar `Serial.begin(115200)` y llamar a la función después de cada adquisición, por ejemplo cada 500 ms. No se incluye un sketch que fabrique mediciones ni se asignan pines desconocidos.

## Actualidad y origen

Cada pieza tiene su propia hora de recepción UTC, asignada por el computador, y caduca a los 5 segundos sin un mensaje nuevo para esa pieza. Se usa un reloj monotónico para el tiempo transcurrido. Esta hora corresponde a recepción, no al instante físico de medida: el firmware debe enviar adquisiciones nuevas, no repetir una muestra guardada indefinidamente. No existe todavía sincronización del reloj del Arduino ni detección de repetición de muestras.

La aplicación distingue: sin conexión, esperando esa pieza, lectura vigente y lectura vencida. Ante pérdida del backend deja de mostrar los valores como actuales y reintenta la consulta. Ante caída del puerto libera el recurso y requiere volver a conectar. Las lecturas vencidas o faltantes no se sustituyen con datos simulados. La simulación sigue disponible como origen separado. Las animaciones de agua y agujas siguen siendo escenarios matemáticos independientes: los cuatro sensores actuales no identifican por sí solos estados de válvula, presión exacta de cada manómetro o funcionamiento del motor.

## Pendiente para la placa física

Falta conocer la placa Arduino, los módulos de adquisición, el cableado, las salidas reales de los EPT1000 y del caudalímetro y las conversiones/calibraciones usadas. El PT100 requiere su adquisición correspondiente; la curva nominal de resistencia no identifica por sí sola el módulo instalado. La API espera unidades físicas, no voltios, cuentas ADC o pulsos sin convertir. No se ha validado en hardware esta integración.

No se guarda historial todavía: solo la última muestra de cada sensor, su hora y los contadores. Los controles de conexión son locales al computador. Rutas disponibles: `GET /api/serie/puertos`, `POST /api/serie/conectar`, `POST /api/serie/desconectar`, `GET /api/lecturas`; contrato completo en `/docs`.

## Verificación

- `./.venv/Scripts/python.exe scripts/check_serial.py`: parser, paquetes parciales, límites, caducidad por sensor, errores y recuperación de líneas; usa un puerto ficticio sin abrir hardware.
- `python scripts/check_serial_ui.py`: respuestas interceptadas en un navegador de prueba; selección de origen, recepción, caducidad, desconexión, ausencia de mezcla con simulación y móvil.
- Las pruebas no publican lecturas ficticias en el receptor activo.

Referencias de implementación: [API pySerial](https://pyserial.readthedocs.io/en/latest/pyserial_api.html), [Arduino Serial.begin](https://docs.arduino.cc/language-reference/en/functions/communication/serial/begin/), [Arduino Serial.println](https://docs.arduino.cc/language-reference/en/functions/communication/serial/println/).
