# Luma 0.3.6

Para Ubuntu/Debian con GNOME 50 y Wayland.

1. Cierra Luma. Abre el .deb con el instalador gráfico y acepta instalar la actualización.
2. Cierra sesión en Ubuntu y vuelve a entrar para cargar la extensión actualizada.
3. Abre Luma desde el menú de aplicaciones y pulsa Aplicar como fondo con el video seleccionado.

Luma activa su extensión automáticamente. Sin recorte ni fundido usa directamente el original. No necesitas comandos. Al instalar por primera vez, GNOME puede requerir cerrar sesión y volver a entrar para descubrir la extensión; la app lo indica. No se cierra tu sesión automáticamente.

Entrada, salida y fundido son opcionales; pulsa Aplicar después de cambiarlos. Vista previa no cambia el fondo. Detener fondo recupera el fondo estático. Cerrar la ventana mantiene el video. Los originales no se modifican.

La app muestra errores de activación y espera confirmación de carga del reproductor. Las opciones de pausa por batería o pantalla completa pueden pausar el video; desmárcalas para reproducción continua.

El paquete declara GTK, FFmpeg y códecs GStreamer como dependencias. No soporta KDE, X11 ni otras versiones de GNOME. Una extensión antigua instalada con install.sh en el directorio del usuario puede tener prioridad sobre la del paquete y requiere migración.

Validación: pruebas de configuración, activación y errores, codificación real con FFmpeg, caché y simulación de políticas de extensión. Se comprobó la API instalada de Mutter 50. La prueba visual requiere una sesión gráfica de GNOME.

El código fuente y las pruebas están incluidos. build-deb.py reconstruye el paquete. install.sh se conserva como herramienta heredada de desarrollo.
