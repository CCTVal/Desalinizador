# Simulación de los instrumentos

Se revisaron las ecuaciones y se añadieron lecturas estacionarias calculadas a los instrumentos identificados por el usuario. El modelo no está calibrado con la planta. Las fichas del CAD y el bloque «Sensores · lecturas simuladas» comparten resultados. Los controles cambian un escenario local; no actúan sobre equipos reales.

## Ubicaciones e hipótesis

Los sensores 103 y 106 y los manómetros 74 y 72 se encuentran junto a la subida. El sensor de flujo 136 y el PT100 120 están en el colector, antes de la derivación del aspersor. Esta topología se infiere del CAD y del recorrido existente; debe comprobarse en la instalación. El código usa IDs internos una unidad menores que los números del visor.

`datos/simulacion-sensores.json` conserva las cotas aproximadas de los centros de los instrumentos en el CAD, que no son cotas certificadas de sus tomas. Las diferencias de elevación se conservan al trasladar toda la planta. El escenario representa las dos tomas de presión en el mismo conducto de impulsión y supone velocidades equivalentes. El caudalímetro y el PT100 se asignan al caudal común antes de su reparto.

## Matemática hidráulica revisada

La tabla de bomba y la solución del punto de trabajo se mantienen: intersección por bisección, afinidad por frecuencia y ninguna extrapolación fuera de la curva publicada. En cada solución se verifica:

- Continuidad: `Qtotal = Qaspersor + Qdescarga`.
- Balance de carga: `Hbomba = Hestática + (0,25 K + Kllave) Qtotal² + h`.
- Potencia hidráulica: `Ph = Δp · Q`, con Q en m³/s; `Q[m³/s] = Q[L/min]/60000`.

La pieza 136 muestra `Qtotal`, que puede quedar por debajo de sus 10 L/min declarados. Se conserva el valor calculado y se avisa del rango; no se convierte en una lectura garantizada ni se recorta a 10 L/min.

Las presiones locales se reconstruyen hacia aguas arriba desde la presión del nodo del aspersor, usando Bernoulli simplificado:

`pi[bar] = ρ g [h + zaspersor − zi + Ki Qtotal²] / 100000`

Aquí Q está en m³/h, ρ=1000 kg/m³ y g=9,81 m/s². `Ki = 0,25 K · Li/L` reparte las pérdidas comunes por longitud restante hasta la derivación; la pérdida de la llave de alimentación queda aguas arriba de las tomas. La subida idealizada comienza en −0,2188 m, el colector está en 1,458 m, su longitud es 1,528 m y la boca del aspersor está en 1,4159 m. Las cotas del centro de 103 y 106 son 0,163448706 y 1,051239074 m. No se vuelven a sumar todas las pérdidas ni se asigna la Δp de la bomba directamente a cada instrumento.

Este reparto de K es una hipótesis. Faltan diámetros interiores, rugosidades y accesorios para un cálculo de Darcy–Weisbach por tramo. Se supone que la diferencia de carga cinética es despreciable; la boquilla conserva la resistencia concentrada del modelo anterior. La carga estática ajustable es una frontera equivalente, no una reconstrucción del nivel real del tambor. Las presiones están referidas al ambiente. La revisión verifica consistencia y unidades bajo estos supuestos, no exactitud experimental.

Referencia de continuidad, pérdidas y emisores: [manual de EPANET, modelo de red](https://epanet-manual.readthedocs.io/en/latest/3_network_model.html).

## Temperatura y PT100

El caudal por sí solo no determina la temperatura. Se añaden dos condiciones de escenario: temperatura de entrada (20 °C iniciales) y calor neto entregado al agua antes del PT100 (0 W iniciales). Para flujo positivo:

`T120 = Tentrada + Pcalor / (ṁ cp)`

`ṁ = ρ Qtotal[L/min]/60000`, con `cp = 4180 J/(kg·K)`.

El ejemplo de control independiente es 60 L/min, entrada de 20 °C y 4180 W: salida de 21 °C. A 30 L/min, la misma potencia da 22 °C. Con 0 W, cambiar el caudal no calienta el agua. El calor es neto y supuesto; no presupone que haya un calentador ni transforma los 1,1 kW nominales del motor en calor. No incluye recirculación térmica, acumulación, transporte transitorio ni tiempo de respuesta de la sonda. Para evitar representar hielo o vapor con propiedades constantes de agua, el escenario térmico se restringe al intervalo abierto de 0 a 100 °C aunque el instrumento tenga un rango mayor.

La ficha muestra además la resistencia ideal PT100 calculada con Callendar–Van Dusen: `R=100(1+A T+B T²)` para T≥0, añadiendo `100 C(T−100)T³` para T<0; A=3,9083×10⁻³, B=−5,775×10⁻⁷ y C=−4,183×10⁻¹². A 20 °C corresponde 107,7935 Ω. No se simulan errores de cables, tolerancia, adquisición ni un protocolo digital desconocido.

Referencias: [DOE, balance térmico con caudal másico](https://www.energy.gov/sites/default/files/2026-04/DOE-HDBK-1012-92_VOL1.pdf), [BIPM, termometría industrial de platino](https://www.bipm.org/documents/20126/41773843/BIPM_CCT_Guide_to_IPRTs.pdf).

## Estados y ejemplo

Con la bomba apagada, frecuencia cero o alimentación cerrada, se muestra caudal cero por la hipótesis de ausencia de circulación pasiva. La presión residual y la temperatura estancada quedan sin estimación. Con circuito desconectado, valores hidráulicos inválidos o punto fuera de la curva, todas las lecturas quedan desconocidas. Una entrada térmica inválida bloquea solo el PT100. Mover un instrumento o una pieza del circuito más de la tolerancia existente bloquea la simulación. Aislar visualmente una pieza no altera los cálculos.

Las dos agujas 3D usan sus propias presiones locales y se ocultan cuando no se conoce la presión; su interpolación visual de 250 ms no representa dinámica física. Los valores fuera de rango siguen disponibles para diagnóstico, con aviso; el giro de la aguja se limita a la escala dibujada.

Ejemplo: 50 Hz, alimentación al 100 %, descarga abierta, K=40, carga estática=1 m, entrada=20 °C y calor=0 W:

| Instrumento | Resultado calculado |
| --- | --- |
| Presión 103 | 10,41 bar |
| Presión 106 | 9,58 bar |
| Flujo 136 | 27,54 L/min |
| Temperatura 120 | 20,00 °C / 107,79 Ω |
| Manómetro 72 | 9,44 bar |
| Manómetro 74 | 10,25 bar |

`node scripts/check_sensors.mjs` verifica 40 puntos válidos, conservación, unidades, diferencias de presión, calor, resistencia y límites. `python scripts/check_sensors.py` verifica controles, fichas vivas, estados de fallo y móvil. `python scripts/check_gauge.py` verifica las agujas en el CAD. `node scripts/check_pump.mjs` comprueba la curva y el reparto de ramas.
