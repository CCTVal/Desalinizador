# Ficha técnica de equipos e instrumentos

Información entregada por el usuario el 12 de noviembre de 2026. Pendiente de contrastar con placas o fichas del fabricante. La versión estructurada está en `datos/equipos.json`.

| Equipo | Especificaciones declaradas |
| --- | --- |
| Bomba vertical multietapa | WDM VSSE 1-23; cuerpo de acero inoxidable 304; conexiones de 32 mm. Motor: 1,1 kW; 1,5 HP; 380 V; 50 Hz. |
| Manómetros analógicos · piezas 72 y 74 | Medidor de presión no digital, identificado por el usuario. Diámetro declarado: 100 mm; conexión 1/2 pulgada NPT; rango 0–70 bar. |
| Sensor de temperatura · pieza 120 | PT100 de 3 hilos; bulbo de acero inoxidable SS 316L; diámetro 6,35 mm; rango −50 a 250 °C. Pieza identificada por el usuario. |
| Sensores de presión · piezas 103 y 106 | Volltell EPT1000; rango 0–100 bar. Identificados por el usuario como sensores digitales. |
| Sensor de flujo de agua · pieza 136 | Rango 10–100 L/min; marca y modelo pendientes. Identificado por el usuario. |
| Ventilador grande | TD 1000/200 Silent 3V; potencia absorbida máxima 130 W; potencia en mínimo declarada 120 W; intensidad absorbida máxima 0,55 A. |

## Uso en el gemelo digital

Estas especificaciones describen los equipos; no son lecturas en tiempo real. Los rangos del manómetro (0–70 bar) y del sensor de presión (0–100 bar) son distintos y se conservan por separado. Ninguno define por sí solo la presión de trabajo de la planta o las alarmas.

El rango del sensor de flujo no determina el caudal de la bomba. La conexión de 32 mm corresponde a la bomba; no se asigna como diámetro interior de todo el circuito. Las potencias del motor y del ventilador permanecen separadas.

Se incorporó la tabla H-Q oficial WDM de referencia para VSSE1-23 a 50 Hz en `datos/bomba-vsse1-23.json`. El panel de bomba estima un punto de trabajo con esa tabla y una curva supuesta del circuito; el avance visual responde al caudal estimado. Falta confirmar la tabla con la unidad instalada y calibrar pérdidas a partir de cotas, diámetros interiores, válvulas y accesorios reales. Para representar el vaciado del tambor faltan su geometría interior, capacidad y nivel inicial. Las potencias hidráulica y de referencia de eje no son consumo eléctrico medido; ver `modelo-bomba.md`.

La asociación provisional de la bomba a los sólidos internos 182 y 183 se apoya en las alturas CAD de 643/241 mm, compatibles con el catálogo. Debe confirmarse en el montaje. El usuario identificó las piezas 72 y 74 del visor (IDs internos 71 y 73) como manómetros analógicos; se mantienen separadas del sensor de presión Volltell EPT1000. Las piezas 103 y 106 del visor (IDs internos 102 y 105) corresponden a sensores de presión Volltell EPT1000, confirmados por el usuario. La pieza 136 del visor (ID interno 135) corresponde al sensor de flujo de agua, confirmado por el usuario. La pieza 120 del visor (ID interno 119) fue identificada por el usuario como sensor de temperatura y se asocia al PT100 registrado. Las demás asociaciones siguen pendientes. También faltan las señales de salida y la adquisición de los sensores para conectarlos al backend.

Las lecturas simuladas y sus límites se describen en [simulacion-sensores.md](simulacion-sensores.md). La presión usa cotas y pérdidas supuestas; el PT100 usa temperatura de entrada y calor neto configurables. No se dispone de telemetría real.
