# Gemelo digital de planta

<!-- impeccable:product-schema 1 -->

## Platform

web local en Windows.

## Stack

Python y FastAPI para el backend, Three.js para el visor. Vite construye el frontend. OpenCascade convierte el STEP a GLB. SQLite está contemplado para una etapa posterior y aún no está integrado.

## Product Purpose

Explorar en el navegador el diseño de planta `P23.00-00-A008v2.stp`, versión vigente entregada por el usuario. El usuario solicita partir del diseño real y aplicar las skills Ponytail y Anatomy. El proyecto tiene como objetivo futuro combinar sensores y simulación y representar el agua.

## Assets and Constraints

Conservar el STEP original. La visualización es una malla triangulada derivada. Los datos y nombres visibles proceden del CAD. No presentar mediciones inventadas como sensores ni una animación como simulación física. Instalación de las skills dentro del proyecto.

## Open Decisions

El usuario confirmó que las lecturas futuras llegarán desde un Arduino por puerto serie. Existe recepción local por pySerial, selección explícita de puerto/baudios y mensajes JSON por línea para las piezas 103, 106, 136 y 120. Se separan simulación y datos recibidos, con caducidad individual de 5 segundos. Pendientes placa, módulos, cableado y calibración; no se ha probado hardware físico ni se almacena historial. Contrato en `documentacion/arduino-serie.md`.

El panel de bomba usa `datos/bomba-vsse1-23.json`: tabla oficial Q-H WDM de 50 Hz, afinidad para frecuencia simulada y una curva supuesta del circuito. Permite cambiar frecuencia y apertura y observar caudal, incremento de presión, potencia hidráulica y una referencia de potencia de eje por afinidad. No estima consumo eléctrico real. La calibración de pérdidas, la equivalencia exacta de la curva con la unidad instalada, la adquisición de sensores y la existencia de un variador físico siguen pendientes. La potencia nominal de 1,1 kW no se modifica al mover los controles.

Las especificaciones declaradas por el usuario para seis equipos e instrumentos están registradas en `datos/equipos.json` y `documentacion/ficha-tecnica.md`. La bomba es WDM VSSE 1-23, motor de 1,1 kW a 380 V y 50 Hz. La asociación exacta con sólidos CAD y las curvas de funcionamiento siguen pendientes. Los rangos de instrumentación no se usan como valores de operación ni de alarma.

Audiencia y uso operativo por confirmar. Identificación funcional de equipos, puertos, estanques, sensores, ejes de montaje y capacidades hidráulicas pendientes de validar. No se solicitó publicar el diseño CAD fuera del proyecto.

## Interacción del agua

El usuario confirma que el agua debe continuar después de la bomba hasta la descarga final, no que la cámara siga automáticamente el frente. El trazado llega por el colector superior y la bajante derecha al tubo interno 171, dentro del recipiente 145. La llegada no detiene la animación. El recipiente se hace translúcido para observarla, sin calcular nivel ni llenado. El usuario identifica la llave 167 · P23.00-00-0078 para abrir/cerrar al pulsarla: comienza abierta; cerrarla bloquea la descarga por la bajante mientras sigue el aspersor. El modelo estima el reparto de caudal entre estas dos ramas y distingue presión del aspersor y Δp de bomba usando resistencias supuestas. No hay boquilla calibrada ni sensores conectados.

El usuario pide que las piezas del CAD se conecten físicamente y rechaza la manguera añadida. Eligió ajustar la altura del soporte del tambor. El visor recoloca como conjunto el tambor, su llave, tubos y soporte (13 sólidos), girando 180° y alineando las bocas de los tubos 210 y 124. Se baja el conjunto 26,498 mm y se acortan las patas del soporte 22,998 mm para conservar el apoyo en suelo. La manguera se elimina. El recorrido pasa por la llave verde 208 y continúa hasta la entrada de la cañería. Al separar piezas se detiene el flujo. El CAD fuente permanece intacto; el ajuste del soporte y las nuevas posiciones se aplican en el montaje visual propuesto. Se conservan zoom, giro/desplazamiento de vista, selección, aislamiento, edición X/Y/Z y restauración al montaje conectado. No hay caudal/presión calibrados, sensores, llenado ni validación de fabricación o sellado.
