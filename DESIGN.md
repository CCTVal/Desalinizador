---
name: "PLANTA · Explorador 3D"
description: "Marco técnico neutro para explorar el CAD real, pieza por pieza."
colors:
  page-light: "#f2f2ef"
  card-light: "#fbfbfa"
  text-light: "#57575a"
  strong-light: "#18181a"
  mid-light: "#8a8a8f"
  faint-light: "#d4d4d6"
  page-dark: "#0b0b0b"
  card-dark: "#131313"
  text-dark: "#a3a3a3"
  strong-dark: "#e6e6e6"
  mid-dark: "#6a6a6a"
  faint-dark: "#2a2a2a"
  selected-mesh: "#b48a44"
  neutral-mesh: "#9ea4a5"
typography:
  headline:
    fontSize: "clamp(28px, 3vw, 42px)"
    fontWeight: 550
    letterSpacing: "-.035em"
  title:
    fontSize: "16px"
    fontWeight: 600
  body:
    fontSize: "13px"
    lineHeight: 1.65
  label:
    fontSize: "12px"
  readout:
    fontFamily: "ui-monospace, SF Mono, Menlo, Consolas, monospace"
    fontSize: "11px"
rounded:
  part: "3px"
  control: "6px"
  viewer: "12px"
spacing:
  control-gap: "8px"
  section: "22px"
  workspace: "30px"
components:
  button:
    rounded: "{rounded.control}"
    padding: "7px 12px"
  button-pressed-light:
    backgroundColor: "{colors.strong-light}"
    textColor: "{colors.card-light}"
    rounded: "{rounded.control}"
    padding: "7px 12px"
  button-pressed-dark:
    backgroundColor: "{colors.strong-dark}"
    textColor: "{colors.card-dark}"
    rounded: "{rounded.control}"
    padding: "7px 12px"
  search:
    rounded: "{rounded.control}"
    padding: "9px 10px"
    width: "100%"
  viewer:
    rounded: "{rounded.viewer}"
  part:
    rounded: "{rounded.part}"
    padding: "8px"
    width: "100%"
---

# Design System: PLANTA · Explorador 3D

## Overview

**Creative North Star: "El CAD como protagonista"**

El sistema existente presenta una herramienta local de exploración del diseño real. Un marco técnico de Anatomy rodea la escena de Three.js: identificación y orientación arriba, instrucciones y lectura de estado abajo. Los controles y el inventario acompañan la geometría; la superficie no funciona como una landing page ni como una propuesta de identidad de marca.

La densidad se concentra en información útil para inspeccionar las 210 piezas derivadas del STEP. Los dos temas son neutros, las superficies son planas y la vista inicial es isométrica ortográfica. Los colores originales pertenecen al CAD; la interfaz distingue la selección sin atribuirle un estado operativo.

**Key Characteristics:**

- Modelo real como foco visual.
- Marco, título y lectura de estado en los bordes de la figura.
- Controles compactos y panel de inspección subordinado.
- Temas claro y oscuro de Anatomy, sin decoración de telemetría.

Registro descriptivo basado en `index.html`, `src/style.css`, el CSS importado `.agents/skills/anatomy/kit/iso.css`, `src/main.js`, `PRODUCT.md`, `documentacion/visualizacion.md` y las capturas `planta-desktop.png`, `planta-mobile.png`, `planta-dark.png` y `planta-3d.png`. Los tokens registran el uso actual; no convierten todos los recursos disponibles del kit en reglas del visor.

## Colors

La interfaz usa grises cálidos claros y grises oscuros, reservando el color material al modelo y a su selección.

### Primary

- **Ocre de selección** (`selected-mesh`): reemplaza temporalmente el material de la pieza seleccionada en la escena; no es un acento de marca ni una alarma.

### Neutral

- **Página / tarjeta** (`page-light`, `card-light`, `page-dark`, `card-dark`): separan el fondo de trabajo del marco y del fondo de la escena. El tema inicial es claro.
- **Texto fuerte / texto auxiliar** (`strong-*`, `text-*`): títulos, controles y cifras frente a descripciones, instrucciones y metadatos.
- **Borde tenue / borde medio** (`faint-*`, `mid-*`): divisores, contornos de campos y botones; el borde medio aparece al pasar sobre botones habilitados y en la barra de desplazamiento.
- **Material neutro** (`neutral-mesh`): opción explícita para inspeccionar forma sin los materiales originales del CAD.

Los nombres de token con sufijo de tema representan las variables de Anatomy del mismo rol. Los botones pulsados invierten fuerte y tarjeta; las filas seleccionadas del inventario usan borde tenue como fondo y conservan texto fuerte. Los rojos, verdes, azules y tonos de sólidos SVG disponibles en Anatomy no forman parte de la UI observada.

## Typography

La jerarquía separa el título de página, los títulos de sección, la información auxiliar y la lectura técnica. La identificación del modelo y el zoom usan la pila monoespaciada de Anatomy; las cifras del panel usan números tabulares.

- **Headline:** título principal fluido, con peso y espaciado definidos en el frontmatter.
- **Title:** encabezados de inspección e información del modelo.
- **Body:** descripciones del panel lateral; la introducción usa un tamaño mayor (15px).
- **Label:** controles compactos y filas de piezas; las notas inferiores usan tamaño menor (11px).
- **Readout:** zoom y conteo al pie de figura; la identificación superior del modelo usa la misma familia a tamaño de etiqueta (12px).

Observación no canonizada: la aplicación usa actualmente `'Segoe UI', sans-serif` como fuente general. Es una elección de sistema presente en el código, no una voz tipográfica de marca aprobada ni una recomendación para extender la identidad. No se propone una sustitución en este registro.

## Layout

El contenido se centra con un ancho máximo (1680px), margen horizontal relativo (3.4%) y espacio superior (40px). Una introducción breve precede al área de trabajo. En escritorio, la escena ocupa la columna flexible y el panel lateral ocupa (300px), separados por el token `workspace`.

Hasta (1000px), el panel se reduce a (250px), el espacio entre columnas a (20px) y se oculta el estado central de la cabecera. Hasta (760px), el área de trabajo se apila: figura primero, información e inventario después. El contenido usa márgenes laterales (16px), la cabecera simplifica el descriptor y el pie se apila. No hay navegación móvil adicional.

El viewport usa `clamp(400px, 53vh, 720px)` en escritorio y altura fija (420px) en móvil. Los bordes superior e inferior del marco alojan título, orientación, ayuda y estado. Los botones de cámara se distribuyen en filas encima del viewport, sin superponerse a la geometría; la barra de acciones se separa por una línea. El panel lateral divide sus secciones con borde y el espacio `section`. El inventario desplaza su propia lista, con altura máxima (176px), ampliada a (210px) en móvil.

## Elevation & Depth

La interfaz es plana: no aplica sombras ni desenfoques a tarjetas o controles. La diferencia de tonos y los bordes finos separan página, figura, herramientas y panel. La profundidad de la escena procede de la geometría real, la proyección ortográfica y las luces de Three.js. Las sombras y animaciones SVG disponibles en el kit importado no se usan en esta superficie.

## Shapes

La figura tiene esquinas suavizadas con el token `viewer`, recorta su contenido y usa borde fino (1px). Los botones y el buscador comparten el token `control`; las filas del inventario usan el radio menor `part`. Los separadores del panel son rectos. El símbolo de cabecera es un cubo trazado; no establece una biblioteca de iconos para acciones inexistentes.

## Components

### Buttons

Controles compactos y textuales, sin jerarquía promocional. La variante habitual usa tarjeta, texto fuerte y borde tenue; altura mínima (36px). La variante de tema es transparente. Los botones de orientación tienen altura mínima (34px), tamaño de etiqueta y relleno reducido (6px 10px).

El borde cambia a medio al pasar sobre un botón habilitado. El estado pulsado invierte los colores; el foco visible usa contorno fuerte (2px) separado (4px). Los deshabilitados usan opacidad (.42). No hay transición animada declarada. Orientaciones, encuadre, giro, PNG y mostrar todo permanecen deshabilitados hasta cargar la geometría. Aislar requiere una pieza seleccionada.

### Search and material control

El buscador ocupa todo el ancho del panel, con fondo de tarjeta, borde tenue, texto fuerte y placeholder auxiliar. Comparte el foco visible general. Su etiqueta permanece fuera del campo y el contador muestra coincidencias reales. El checkbox de material neutro es nativo (15px), con acento fuerte y etiqueta auxiliar; no es un estado de sensor.

### Inventory rows

Filas de botón a ancho completo, alineadas a la izquierda, sin borde y con fondo transparente. Permiten partir nombres largos y muestran número y nombre CAD. La fila pulsada cambia a fondo tenue; su selección se sincroniza con la escena y con el panel de inspección.

### Viewer frame

Contenedor técnico de la escena, no tarjeta de marketing. La cabecera y el pie distribuyen sus dos extremos con flex; en móvil el pie se apila. Una capa de carga ocupa el viewport hasta que se obtiene geometría y metadatos; si falla, contiene un mensaje de error. Los fragmentos del sidecar representan el marco y sus estados, no reproducen una escena WebGL ficticia.

### Camera and selection

Ocho orientaciones ortográficas: isométrica, isométrica posterior, frontal, posterior, izquierda, derecha, superior e inferior. La escena permite giro, zoom y selección con puntero o teclado; la lista ofrece una segunda vía para piezas pequeñas. El giro automático es voluntario, a velocidad (.16 rad/s), y no se ejecuta con movimiento reducido, documento oculto o viewport por encima del área visible. Los cambios de vista y tema no tienen transición de interfaz declarada.

## Do's and Don'ts

### Do:

- **Do** mantener la geometría real como foco y los controles como apoyo a la inspección.
- **Do** mantener identificación, orientación, ayuda y lectura de estado en el marco de la escena.
- **Do** conservar la correspondencia entre selección de malla, inventario y panel.
- **Do** reflejar carga, disponibilidad de acciones y movimiento reducido con los estados implementados.

### Don't:

- **Don't** presentar el ocre de selección como alarma, sensor o acento de marca.
- **Don't** presentar la apertura visual o el chorro ilustrativo como mediciones de sensores o simulación hidráulica calibrada.
- **Don't** convertir los recursos SVG no usados de Anatomy en requisitos de esta malla importada.
- **Don't** tratar la orientación visible o la envolvente CAD como validación de instalación o cotas certificadas.
