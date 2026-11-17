# Modelo inicial de la bomba WDM VSSE 1-23

El panel permite encender/apagar la bomba, variar una frecuencia simulada de 0–50 Hz, ajustar la llave de alimentación y abrir/cerrar la llave de descarga **167 · P23.00-00-0078**. Esta última empieza abierta y responde al clic sobre el CAD o su etiqueta, sin aislar la pieza ni mover sus bocas. Se mantienen la potencia nominal del motor (1,1 kW), tensión de placa (380 V) y conexiones declaradas (32 mm). La variación de frecuencia supone un variador virtual; no se ha confirmado ni controlado un variador físico.

## Fuentes

La tabla Q-H de referencia está publicada por [WDM Pumps Argentina](https://wdmpumps.com/ar/bombas-multietapas-verticales-en-acero-inoxidable-vsse/) para el modelo VSSE1-23, referencia 1G0220. El [catálogo oficial de 50 Hz](https://wdmpumps.com/ar/wp-content/uploads/2023/01/Catalogo-VSSE-Multietapa-20-01-23.pdf), página PDF 14 (impresa 12), confirma 1,1 kW y los puntos de la tabla. Se consultó el 12 de noviembre de 2026.

La curva se almacena en `datos/bomba-vsse1-23.json`, con caudales de 0,4 a 2,2 m³/h y alturas de 135 a 80 mca. No se inventan puntos a caudal cero, ni se extrapola fuera del tramo publicado. La correspondencia con la unidad instalada todavía debe confirmarse con su placa y variante exacta.

Se usan las [leyes de afinidad de bombas](https://www.ksb.com/en-global/centrifugal-pump-lexicon/article/pump-affinity-laws-1117584) para diámetro constante, aproximando la relación de velocidades por f/50: Q escala con r, H con r² y una referencia de potencia con r³. Es una aproximación que no modela deslizamiento, refrigeración ni pérdidas eléctricas del motor.

## Cálculo

`src/pump-model.js` interpola linealmente H50(Q). Para r=f/50, usa H(Q,f)=r²·H50(Q/r). El punto de trabajo es la intersección con el circuito supuesto:

`Hcircuito(Q) = Hestática + [0,25·K + 20·(1/a² − 1)]·Q² + h`

Q está en m³/h, a es la fracción de apertura de alimentación y h es la carga de presión en el nodo del aspersor, referida a su salida. Por defecto Hestática=1 m y K=40 m/(m³/h)². K es un coeficiente de referencia: se asigna el 25 % a pérdidas comunes. Las resistencias terminales se fijan como supuestos independientes, de forma que la resistencia equivalente inicial con descarga abierta se aproxima al K anterior. La ley de la llave de alimentación y todos estos coeficientes son supuestos, sin calibración con la planta. Se ignoran transitorios, golpe de ariete, caudal inverso, cavitación, NPSH y vaciado del tambor.

Los dos ramales comparten presión y conservan caudal:

- `Qaspersor = √[max(0,h) / 270]`.
- `Qdescarga = √[max(0,h + 1,6222) / 67,5]` con llave 167 abierta; cero cuando está cerrada.
- `Q = Qaspersor + Qdescarga`.

Las resistencias 270 y 67,5 tienen unidades m/(m³/h)² y no proceden de la ficha de la boquilla ni de la válvula. La diferencia vertical 1,6222 m corresponde aproximadamente a las cotas de la boca del aspersor y del tubo final del CAD. Se supone presión atmosférica en la columna y en el recipiente, velocidad de salida incorporada a la resistencia y ausencia de otras ramas abiertas. La carga estática común sigue siendo ajustable y supuesta, no una reconstrucción completa del circuito.

Se resuelve primero h para cada Q, y luego el punto de trabajo contra la curva de la bomba. La presión mostrada en el aspersor es `max(0,h)·ρg`, distinta de Δp de la bomba. El modelo reproduce mayor presión y caudal en el aspersor al cerrar la descarga, con menor caudal total. A 50 Hz y alimentación al 100 %, los supuestos iniciales dan aproximadamente 7,93 bar en el aspersor con descarga abierta y 12,34 bar con descarga cerrada. Son resultados del ejemplo, no valores predichos para la planta real. El comportamiento cualitativo se apoya en el cambio del [punto de trabajo por estrangulación (KSB)](https://www.ksb.com/en-global/centrifugal-pump-lexicon/article/control-by-throttling-1116808) y en la relación caudal-presión de emisores descrita en el [manual de EPANET (EPA)](https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=P10113EM.TXT).

La función conserva el modo anterior de circuito equivalente cuando no recibe el estado `bypassOpen`; el visor siempre utiliza el cálculo con los dos ramales.

Se resuelve la intersección por bisección, únicamente entre los caudales tabulados escalados. Si no está acotada, se muestran guiones y «Fuera del tramo de curva publicado», en vez de inventar un caudal o mostrarlo como cero. Con la llave de alimentación cerrada Q=0, pero la presión atrapada se deja desconocida: no hay modelo de transitorios ni punto tabulado a caudal cero. Cerrar solo la llave 167 mantiene abierto el ramal del aspersor.

Se calcula Δp=ρgH y potencia hidráulica Ph=Δp·Q, tomando ρ=1000 kg/m³ y g=9,81 m/s². Δp es el incremento equivalente de carga aportado por la bomba, no una lectura de presión absoluta o de un sensor de la planta. La referencia `1,1·r³ kW` usa la potencia nominal como escala: **no es una predicción del consumo eléctrico ni de la potencia de eje real en cada punto**. No hay medición ni modelo de rendimiento completo.

## Integración visual

El movimiento de los trazadores es proporcional al caudal calculado. Su escala de pantalla no representa la velocidad física dentro de los tubos, cuyo diámetro interior no está confirmado. No se modifica el diámetro del CAD para simular mayor caudal. El recorrido incluye el tambor, la unión realineada, la llave verde, la base de la bomba, la columna de subida, el colector superior y la llave y bajante derechas hasta el tubo de descarga final (ID interno 171). Este tubo termina dentro del recipiente 145. Los codos superiores usan curvas con tangentes alineadas con las bocas CAD. El interior multietapa se representa como un equipo concentrado, no como CFD o una reconstrucción de los impulsores.

Con la llave 167 abierta, al llegar a la descarga los marcadores siguen animándose como una corriente continua, sin dibujar ni afirmar un retorno desde el recipiente al tambor. Al cerrarla, el tramo inferior deja de mostrar corriente; la alimentación hacia el aspersor continúa. El trazado hasta la válvula representa agua presente, sin marcadores en movimiento después de la derivación. No se simulan el llenado del recipiente, el vaciado del tambor ni otras ramificaciones. El reparto entre aspersor y descarga es una estimación con las resistencias anteriores.

Los sólidos 182 y 183 (IDs internos) son compatibles dimensionalmente con cuerpo/motor de 643/241 mm del catálogo: la asociación se registra como provisional. El desplazamiento de la bomba, motor o conexiones interrumpe el circuito y bloquea el cálculo de bombeo. El aislamiento solo oculta la animación y no altera el punto de trabajo del circuito intacto.

El aspersor indicado por el usuario como **159 · P23.00-00-0072** (ID interno 158) recibe una derivación del colector. La emisión se sitúa en la boca inferior del conector contiguo (ID interno 159), hacia abajo dentro de la columna 59. La animación espera al frente de agua y termina las trayectorias en la bandeja superior 63; no atraviesa esa bandeja. La pared se transparenta para inspeccionar las gotas. Desplazar el aspersor o su conector interrumpe la simulación como el resto de las conexiones.

La dispersión se limita al interior de la columna; tamaño ampliado y velocidad inicial de las gotas son supuestos visuales. Se dibujan trayectorias descendentes con gravedad de 9,81 m/s². El caudal estimado del ramal del aspersor cambia la densidad de trazadores; la presión estimada cambia una velocidad visual de lanzamiento, escalada a 0,7 m/s a 8 bar. Esa escala no representa la velocidad real de salida. Faltan curva caudal/presión de la boquilla, ángulo, distribución de tamaños y calibración de pérdidas. La presión diferencial de la bomba no se presenta como presión de la boquilla. Con movimiento reducido se muestra un patrón estático de gotas.

El cálculo corre actualmente en el navegador; FastAPI sirve la aplicación y su estado general. Ningún control envía comandos a equipos reales. Las pruebas `check_pump.mjs` comprueban tabla, unidades, afinidad, intersección, parada y límites; `check_pump_ui.py` comprueba que los controles cambien lecturas, gráfica y avance del agua.
