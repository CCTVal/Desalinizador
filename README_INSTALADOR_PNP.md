# Instalador del conversor de componentes CCTVal

1. Copia `ConversorPnP_Instalador.rar` al otro PC.
2. Abre el archivo RAR y extrae `ConversorPnP_Instalador.exe`.
3. Ejecuta el instalador y acepta la carpeta de destino propuesta. Creará accesos directos en el escritorio y en el menú Inicio.
4. Abre **Conversor de archivos de componentes**, elige el CSV original, el destino y la cara de la placa, y pulsa **Convertir**.

El instalador y el programa no necesitan Python en el PC de destino. El archivo `ConversorPnP.exe` de la carpeta `dist` también puede usarse directamente sin instalarlo.

Para volver a crear los paquetes en este proyecto, ejecuta `powershell -ExecutionPolicy Bypass -File .\build_pnp_installer.ps1` desde PowerShell. Se necesitan PyInstaller, PyQt6 y WinRAR en el equipo de compilación.
