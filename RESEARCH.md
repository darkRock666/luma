# Investigación y criterio de producto

Consulta web: 6 de noviembre de 2026. Comparación basada en documentación de los proyectos, no en benchmarks propios. “Mejor” depende del escritorio y del tipo de fondo.

| Herramienta | Dónde destaca | Restricción relevante |
|---|---|---|
| [Hidamari](https://github.com/jeffshee/hidamari) | Interfaz Python, videos, GNOME Wayland, varios monitores y fuentes web | Su README limita la detección de pantalla completa a X11; no asumir comportamiento idéntico en todos los escritorios |
| [Smart Video Wallpaper Reborn](https://github.com/luisbocanegra/plasma-smart-video-wallpaper-reborn) | Integración con Plasma 6, listas, pausas, batería y configuración avanzada de decodificación | Es un plugin de KDE; no sirve como integración de GNOME |
| [mpvpaper](https://github.com/GhostNaN/mpvpaper) | Base pequeña para reproducir videos con mpv en compositores wlroots; control IPC | No aporta biblioteca gráfica; su mecanismo de Wayland no es el de GNOME |
| [Waypaper](https://pypi.org/project/waypaper/) | Selector gráfico para varios motores y monitores | Depende del motor elegido; no uniformiza las capacidades de todos los escritorios |
| [linux-wallpaperengine](https://github.com/Almamu/linux-wallpaperengine) | Uso de fondos de Wallpaper Engine y opciones de escenas, FPS y escalado | Requiere recursos de Wallpaper Engine para muchos fondos; su README excluye una GUI propia y documenta restricciones de compositor |
| [OpenWallpaper](https://openwallpaper.org/) | Runtime de escenas WASM, video con libmpv y separación de interfaz/renderizador | La integración y autopausa dependen del escritorio; su documentación destaca Hyprland para autopausa |

## Decisión para Luma

El equipo de trabajo expone GNOME 50 y Wayland. El primer adaptador apunta a ese entorno y usa GTK 4 para la interfaz/reproducción y una extensión pequeña para integrar la ventana en el fondo. No reutiliza código fuente de los proyectos comparados.

La propuesta de mejora es reducir la configuración necesaria para un usuario de GNOME: biblioteca, vista previa, controles en español, selección local y políticas de ahorro en el mismo flujo. Estas características por sí solas **no demuestran que Luma sea mejor** que Hidamari o el plugin de Plasma; otras herramientas ya ofrecen muchas de ellas. La diferenciación necesita validación con usuarios y mediciones.

## Hoja de ruta con criterios de aceptación

1. Validación GNOME: sin ventana del renderer en Alt-Tab/actividades; detrás de los iconos; recuperación al bloquear y desconectar monitores; sin procesos huérfanos. Actualmente pendiente.
2. Estado verificable: interfaz muestra reproducción/pausa y causa, error de códec y fallo de extensión mediante un canal IPC; no confundir “guardado” con “reproduciendo”.
3. Consumo: comparar el mismo clip 1080p/4K en idéntico equipo, medir CPU, GPU, memoria y potencia durante reproducción/pausa; publicar resultados reproducibles antes de prometer ahorro superior.
4. Adaptadores: mpvpaper para wlroots, plugin nativo para KDE y backend X11; no presentar una ventana normal como si fuera un fondo compatible.
5. Biblioteca avanzada: miniaturas cacheadas, listas por monitor, restauración con archivos ausentes y formatos inspeccionados por códec.
6. Distribución: paquete instalable con comprobación de dependencias y pruebas en hardware Intel/AMD/NVIDIA.

Fuentes técnicas complementarias: [GTK Video](https://docs.gtk.org/gtk4/class.Video.html), [GTK MediaFile](https://docs.gtk.org/gtk4/class.MediaFile.html), [Xwinwrap](https://github.com/mmhobi7/xwinwrap). Las llamadas a Mutter requieren verificación con la versión instalada: la prueba simulada no sustituye esa validación.
