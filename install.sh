#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
/usr/bin/python3 -c 'import gi; gi.require_version("Gtk", "4.0"); from gi.repository import Gtk' || {
  echo 'Instala python3-gi, gir1.2-gtk-4.0 y libgtk-4-media-gstreamer con tu gestor de paquetes.'
  exit 1
}
command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1 || {
  echo 'Falta FFmpeg. Instala el paquete ffmpeg con tu gestor de paquetes.'; exit 1;
}
version=$(gnome-shell --version)
case "$version" in *' 50.'*) ;; *) echo 'Esta versión solo declara compatibilidad con GNOME 50.'; exit 1 ;; esac
ext="${XDG_DATA_HOME:-$HOME/.local/share}/gnome-shell/extensions/luma@local.desktop"
app="${XDG_DATA_HOME:-$HOME/.local/share}/luma"
mkdir -p "$ext" "$app/luma"
cp extension/metadata.json extension/extension.js "$ext/"
cp luma/player.py "$ext/player.py"
cp luma/*.py "$app/luma/"
cp run.py "$app/run.py"
mkdir -p "${XDG_DATA_HOME:-$HOME/.local/share}/applications"
/usr/bin/python3 - "$app" "${XDG_DATA_HOME:-$HOME/.local/share}/applications/local.luma.Studio.desktop" <<'PYDESKTOP'
import sys
from pathlib import Path
# Desktop Entry quoting is not shell quoting.
exe = str(Path(sys.argv[1]) / 'run.py').replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
Path(sys.argv[2]).write_text('[Desktop Entry]\nType=Application\nName=Luma\nComment=Fondos de video con bucles suaves\nExec=/usr/bin/python3 "' + exe + '"\nIcon=video-x-generic\nTerminal=false\nCategories=Utility;AudioVideo;\n')
PYDESKTOP
echo "Instalado en $app y $ext; acceso Luma añadido al menú de aplicaciones."
echo 'Cierra sesión, vuelve a entrar y ejecuta: gnome-extensions enable luma@local.desktop'
echo "Abre Luma con: /usr/bin/python3 \"$app/run.py\""
