# Gemelo digital del desalinizador

Aplicación local para explorar el modelo CAD de la planta, simular su circuito de agua y preparar la recepción de lecturas desde Arduino por USB/puerto serie. El visor está construido con Three.js y Vite; el backend utiliza Python, FastAPI y pySerial.

Esta rama contiene el gemelo digital. Sustituye el contenido anterior de análisis de imágenes de gotas, que sigue disponible en el historial de Git.

## Qué incluye

- Visor 3D de las 210 piezas del modelo `P23.00-00-A008v2.stp`: selección, aislamiento, zoom, giro, desplazamiento y edición temporal X/Y/Z.
- Montaje conectado propuesto, con ajuste visual del soporte del tambor. Los archivos CAD originales se conservan.
- Simulación estacionaria de la bomba WDM VSSE 1-23, usando su curva de referencia a 50 Hz, frecuencia virtual, apertura de alimentación y válvula de descarga.
- Animación del agua hacia el aspersor y la descarga final; interrupción del flujo al separar las piezas del circuito.
- Escalas y agujas animadas integradas en los manómetros 3D de las piezas 72 y 74.
- Lecturas simuladas de presión, caudal y temperatura, con avisos al quedar fuera del rango declarado del instrumento.
- Recepción de mensajes JSON desde Arduino, selección de puerto y baudios, hora de recepción y vencimiento individual de lecturas a los 5 segundos.

## Instrumentos identificados

| Piezas del visor | Instrumento | Rango declarado |
| --- | --- | --- |
| 72 y 74 | Manómetros analógicos | 0–70 bar |
| 103 y 106 | Sensores de presión Volltell EPT1000 | 0–100 bar |
| 136 | Sensor de flujo de agua | 10–100 L/min |
| 120 | Temperatura PT100 de 3 hilos | −50 a 250 °C |

La marca y modelo del caudalímetro siguen pendientes. Las especificaciones están en [datos/equipos.json](datos/equipos.json) y [la ficha técnica](documentacion/ficha-tecnica.md).

## Instalar y ejecutar

Requiere Node.js 20.19+ o 22.12+, Python 3.10+ y un navegador con WebGL. Desde PowerShell:

```powershell
git clone --branch gemelos-digitales --single-branch https://github.com/CCTVal/Desalinizador.git
cd Desalinizador
npm.cmd ci
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
npm.cmd run build
./.venv/Scripts/python.exe -m uvicorn src.server:app --host 127.0.0.1 --port 8001
```

Abre **http://127.0.0.1:8001**. En instalaciones ya preparadas también puedes ejecutar `./iniciar.ps1`. La documentación de la API está en **http://127.0.0.1:8001/docs**.

La copia web del modelo (`public/modelos/planta.glb`) está incluida. Solo hace falta ejecutar `npm.cmd run convert` si quieres regenerarla desde el STEP. Tras cambiar el frontend, ejecuta `npm.cmd run build` y recarga el navegador. `npm.cmd run dev` sirve para desarrollo del frontend; las rutas de recepción serie pertenecen al backend FastAPI.

## Probar la simulación

1. Pulsa **Encender bomba** y aumenta la **Apertura de la llave de alimentación**.
2. Cambia la frecuencia simulada o abre/cierra la llave 167 para observar el reparto de caudales y las presiones.
3. En **Sensores**, pulsa el número de pieza para localizar el instrumento y consultar su ficha actualizada.
4. En **Escenario térmico supuesto**, ajusta la temperatura de entrada y el calor neto al agua. Con 20 °C de entrada y 0 W, cambiar el caudal conserva los 20 °C cuando hay flujo.

Puedes abrir una pieza directamente, por ejemplo [la 74](http://127.0.0.1:8001/?pieza=74) o [la 136](http://127.0.0.1:8001/?pieza=136). Los desplazamientos en el visor son temporales y no modifican el CAD.

## Conectar Arduino

En **Sensores → Conexión Arduino**, selecciona el puerto COM y la velocidad del programa de la placa; después pulsa **Conectar**. Cierra antes el monitor serie del IDE de Arduino. Abrir el puerto puede reiniciar la placa.

El Arduino debe enviar una línea JSON por adquisición, con valores ya convertidos y calibrados. Ejemplo ficticio del formato:

```json
{"lecturas":[{"pieza":103,"valor":8.12,"unidad":"bar"},{"pieza":106,"valor":7.85,"unidad":"bar"},{"pieza":136,"valor":25.4,"unidad":"L/min"},{"pieza":120,"valor":21.6,"unidad":"\u00b0C"}]}
```

El navegador consulta las últimas lecturas cada segundo. Las muestras vencidas o ausentes no se completan con valores simulados. La conexión es compartida por las pestañas y requiere un solo proceso del servidor. Solo se conserva la última lectura por sensor en memoria; todavía no hay historial.

La función [arduino/EnviarSensores.h](arduino/EnviarSensores.h) ayuda a generar los mensajes. El contrato, unidades, estados y pasos completos están en [Arduino por serie](documentacion/arduino-serie.md).

## Alcance del modelo

La simulación utiliza resistencias hidráulicas supuestas y cotas aproximadas del CAD. Se verifican continuidad, balance de carga, potencia hidráulica y balance térmico; falta calibrar pérdidas, validar las tomas y confirmar la curva con la unidad instalada. No es una simulación CFD ni un cálculo validado para fabricación.

La recepción serie se ha probado con datos ficticios y puertos de prueba. Falta integrar y verificar la adquisición con la placa, cableado y módulos reales. Los controles y animaciones de la bomba siguen siendo una simulación independiente y no actúan sobre la planta física.

Ecuaciones y fuentes: [modelo de bomba](documentacion/modelo-bomba.md) y [simulación de sensores](documentacion/simulacion-sensores.md).

## Verificaciones

Pruebas matemáticas y del receptor, sin hardware físico:

```powershell
node scripts/check_pump.mjs
node scripts/check_sensors.mjs
node scripts/check_water.mjs
node scripts/check_assembly.mjs
./.venv/Scripts/python.exe scripts/check_serial.py
```

Para las pruebas del navegador instala Playwright en el entorno de comprobación y su Chromium. Mantén la aplicación ejecutándose en el puerto 8001:

```powershell
./.venv/Scripts/python.exe -m pip install playwright
./.venv/Scripts/python.exe -m playwright install chromium
./.venv/Scripts/python.exe scripts/check_sensors.py
./.venv/Scripts/python.exe scripts/check_gauge.py
./.venv/Scripts/python.exe scripts/check_serial_ui.py
```

## Organización

| Ruta | Contenido |
| --- | --- |
| `src/` | Visor, modelos matemáticos, backend y receptor serie |
| `datos/` | Equipos, curva de bomba y supuestos del circuito |
| `modelos/` | Archivos STEP originales |
| `public/modelos/` | GLB e inventario para el navegador |
| `arduino/` | Función de envío para integrar en la placa |
| `scripts/` | Conversión del CAD y comprobaciones |
| `documentacion/` | Fundamentos, limitaciones y capturas |

El estilo base utiliza el CSS de Anatomy, incluido con su licencia en `.agents/skills/anatomy/`. El repositorio no incluye entornos Python, dependencias Node, compilaciones ni registros de ejecución.
