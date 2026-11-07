#!/usr/bin/env python3
"""Build without root. Requires dpkg-deb; does not install anything."""
from pathlib import Path
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parent
version = '0.3.6'
with tempfile.TemporaryDirectory(prefix='luma-deb-') as tmp:
    stage = Path(tmp)
    def copy(src, dst):
        target = stage / dst
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / src, target)
    for p in (root / 'luma').glob('*.py'):
        copy(p.relative_to(root), Path('usr/share/luma/luma') / p.name)
    copy('run.py', 'usr/share/luma/run.py')
    for name in ('metadata.json', 'extension.js'):
        copy('extension/' + name, 'usr/share/gnome-shell/extensions/luma@local.desktop/' + name)
    copy('luma/player.py', 'usr/share/gnome-shell/extensions/luma@local.desktop/player.py')
    control = stage / 'DEBIAN/control'
    control.parent.mkdir()
    control.write_text('''Package: luma-wallpaper
Version: {version}
Section: utils
Priority: optional
Architecture: all
Maintainer: Luma Local <luma@localhost>
Depends: python3, python3-gi, gir1.2-gtk-4.0, libgtk-4-media-gstreamer, ffmpeg, gstreamer1.0-plugins-good, gstreamer1.0-libav, gnome-shell (>= 50), gnome-shell (<< 51)
Recommends: gstreamer1.0-plugins-good, gstreamer1.0-libav
Description: Video wallpapers with trimmed crossfade loops for GNOME 50
 Spanish GTK interface and cached local video processing.
 Requires GNOME Wayland. Setup is managed in the application.
'''.format(version=version))
    desktop = stage / 'usr/share/applications/local.luma.Studio.desktop'
    desktop.parent.mkdir(parents=True, exist_ok=True)
    desktop.write_text('''[Desktop Entry]
Type=Application
Name=Luma
Comment=Fondos de video con bucles suaves
Exec=/usr/bin/python3 /usr/share/luma/run.py
Icon=video-x-generic
Terminal=false
Categories=Utility;AudioVideo;
''')
    for p in stage.rglob('*'):
        p.chmod(0o755 if p.is_dir() else 0o644)
    stage.chmod(0o755)
    subprocess.run(['dpkg-deb', '--root-owner-group', '--build', str(stage),
                    str(root.parent / f'luma-wallpaper_{version}_all.deb')], check=True)
