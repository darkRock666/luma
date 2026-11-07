import json
import time
import uuid
import threading
from pathlib import Path
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio, Gdk, GLib
from .loop import prepare
from .session import ensure_extension
from .core import load, save, validate_video, config_path

CSS = b'''
window { background: #10141c; color: #eef2ff; }
.hero { font-size: 32px; font-weight: 800; }
.subtitle { color: #a1aec4; font-size: 14px; }
.card { background: #1b2331; border-radius: 16px; padding: 18px; }
button { border-radius: 10px; padding: 9px 16px; }
.primary { background: #b9f27c; color: #10200c; font-weight: bold; }
.status { color: #b9f27c; }
list { background: transparent; }
row { padding: 10px; border-radius: 8px; }
row:selected { background: #30412f; }
'''


class Luma(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='local.luma.Studio')
        self.connect('activate', self.activate_window)
        self.stream = None

    def activate_window(self, *_):
        if self.get_active_window():
            self.get_active_window().present()
            return
        self.data = load()
        self.window = Gtk.ApplicationWindow(application=self, title='Luma · Fondos en movimiento')
        self.window.set_default_size(1000, 720)
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, 600)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        for side in ('top', 'bottom', 'start', 'end'):
            getattr(root, f'set_margin_{side}')(24)
        self.window.set_child(root)
        root.append(self.label('Luma', 'hero'))
        root.append(self.label('Tu escritorio, en movimiento. Videos locales. Sin cuentas.', 'subtitle'))
        self.status = self.label(self.diagnose(), 'status')
        self.status.set_wrap(True)
        root.append(self.status)
        columns = Gtk.Box(spacing=18, vexpand=True)
        root.append(columns)
        library = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, width_request=280)
        library.add_css_class('card')
        columns.append(library)
        library.append(self.label('TU BIBLIOTECA', 'subtitle'))
        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.list.connect('row-selected', self.selected)
        scroll = Gtk.ScrolledWindow(vexpand=True, min_content_height=180)
        scroll.set_child(self.list)
        library.append(scroll)
        library.append(self.button('Elegir video y usar como fondo', self.choose))
        library.append(self.button('Quitar de la biblioteca', self.remove))
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, hexpand=True)
        columns.append(right)
        self.video = Gtk.Video(hexpand=True, vexpand=True)
        self.video.set_size_request(360, 210)
        self.video.add_css_class('card')
        self.video.set_autoplay(False)
        right.append(self.video)
        self.name = self.label('Selecciona un video para comenzar', 'subtitle')
        self.name.set_ellipsize(3)
        right.append(self.name)
        settings = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        settings.add_css_class('card')
        right.append(settings)
        for key, text in [('pause_fullscreen', 'Pausar con una app a pantalla completa'),
                          ('pause_battery', 'Pausar cuando use batería')]:
            check = Gtk.CheckButton(label=text)
            check.set_active(self.data[key])
            check.connect('toggled', self.option, key)
            settings.append(check)
        fit = Gtk.DropDown.new_from_strings(['Rellenar pantalla', 'Mostrar video completo'])
        fit.set_selected(0 if self.data['fit'] == 'cover' else 1)
        fit.connect('notify::selected', self.fit_changed)
        settings.append(fit)
        monitor_row = Gtk.Box(spacing=10)
        monitor_row.append(self.label('Monitor (0 = primero)', 'subtitle'))
        monitor = Gtk.SpinButton.new_with_range(0, 15, 1)
        monitor.set_value(self.data['monitor'])
        monitor.connect('value-changed', self.monitor_changed)
        monitor_row.append(monitor)
        settings.append(monitor_row)
        self.time_inputs = {}
        for key, title, limit in [('trim_start', 'Entrada (segundos)', 86400),
                                   ('trim_end', 'Salida (0 = final)', 86400),
                                   ('crossfade', 'Fundido del bucle (segundos)', 10)]:
            row = Gtk.Box(spacing=10)
            row.append(self.label(title, 'subtitle'))
            spin = Gtk.SpinButton.new_with_range(0, limit, .1)
            spin.set_digits(2)
            spin.set_value(self.data[key])
            self.time_inputs[key] = spin
            row.append(spin)
            settings.append(row)
        settings.append(self.label('El fundido une el final con el inicio. 0 = corte directo.', 'subtitle'))
        controls = Gtk.Box(spacing=10)
        root.append(controls)
        self.apply_button = self.button('Aplicar como fondo', self.apply, 'primary')
        controls.append(self.apply_button)
        controls.append(self.button('Pausar / continuar', self.pause))
        controls.append(self.button('Detener fondo', self.stop))
        controls.append(self.button('Vista previa', self.preview))
        root.append(self.label('GNOME 50 · Wayland  /  Audio desactivado  /  El video sigue al cerrar esta ventana', 'subtitle'))
        self.refresh()
        self.window.connect('close-request', self.close)
        self.window.present()

    def label(self, text, style):
        label = Gtk.Label(label=text, xalign=0)
        label.add_css_class(style)
        return label

    def button(self, text, callback, style=None):
        button = Gtk.Button(label=text)
        button.connect('clicked', callback)
        if style:
            button.add_css_class(style)
        return button

    def diagnose(self):
        return 'Elige un video: Luma activará el fondo automáticamente.'

    def refresh(self):
        while (child := self.list.get_first_child()):
            self.list.remove(child)
        for path in self.data['videos']:
            row = Gtk.ListBoxRow()
            row.path = path
            label = Gtk.Label(label=Path(path).name, xalign=0, ellipsize=3)
            label.set_tooltip_text(path)
            row.set_child(label)
            self.list.append(row)
            if path == self.data['selected']:
                self.list.select_row(row)

    def selected(self, _list, row):
        if row:
            self.data['selected'] = row.path
            self.name.set_text(Path(row.path).name)
            if self.stream:
                self.stream.pause()
            self.stream = Gtk.MediaFile.new_for_filename(row.path)
            self.stream.set_muted(True)
            self.stream.set_loop(True)
            self.stream.connect('notify::error', self.media_error)
            self.video.set_media_stream(self.stream)

    def media_error(self, stream, *_):
        if stream.get_error():
            self.status.set_text('No se pudo decodificar el video: ' + stream.get_error().message)

    def choose(self, *_):
        dialog = Gtk.FileChooserNative(title='Añadir videos', transient_for=self.window,
                                       action=Gtk.FileChooserAction.OPEN, accept_label='Añadir')
        dialog.set_select_multiple(True)
        filt = Gtk.FileFilter(name='Videos')
        filt.add_mime_type('video/*')
        dialog.add_filter(filt)
        dialog.connect('response', self.files_chosen)
        dialog.show()

    def files_chosen(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            files = dialog.get_files()
            try:
                for i in range(files.get_n_items()):
                    path = validate_video(files.get_item(i).get_path())
                    if path not in self.data['videos']:
                        self.data['videos'].append(path)
                    self.data['selected'] = path
                save(self.data)
                self.refresh()
                self.apply()
            except (ValueError, OSError) as e:
                self.status.set_text(str(e))
        dialog.destroy()

    def remove(self, *_):
        path = self.data['selected']
        if path in self.data['videos']:
            self.data['videos'].remove(path)
            self.data.update(selected='', playback='', enabled=False)
            save(self.data)
            if self.stream:
                self.stream.pause()
            self.video.set_media_stream(None)
            self.name.set_text('Selecciona un video')
            self.refresh()

    def option(self, widget, key):
        self.data[key] = widget.get_active()
        save(self.data)

    def fit_changed(self, widget, *_):
        self.data['fit'] = 'cover' if widget.get_selected() == 0 else 'contain'
        save(self.data)

    def monitor_changed(self, widget):
        self.data['monitor'] = widget.get_value_as_int()
        save(self.data)

    def apply(self, *_):
        self.prepare_clip(True)

    def prepare_clip(self, apply):
        if getattr(self, 'preparing', False):
            return
        try:
            filename = validate_video(self.data['selected'])
            times = {key: widget.get_value() for key, widget in self.time_inputs.items()}
        except (ValueError, OSError) as e:
            self.status.set_text(str(e))
            return
        self.preparing = True
        self.apply_button.set_sensitive(False)
        self.status.set_text('Preparando fragmento y fundido… puede tardar según la duración y resolución.')
        if self.stream:
            self.stream.pause()
        def worker():
            try:
                if apply:
                    ensure_extension()
                path = (filename if not any(times.values()) else
                        prepare(filename, times['trim_start'], times['trim_end'], times['crossfade']))
                GLib.idle_add(self.prepared, path, filename, times, apply, None)
            except Exception as e:
                GLib.idle_add(self.prepared, None, filename, times, apply, str(e))
        threading.Thread(target=worker, daemon=True).start()

    def prepared(self, path, filename, times, apply, error):
        self.preparing = False
        self.apply_button.set_sensitive(True)
        if error:
            self.status.set_text(error)
            return False
        if apply:
            # Restore the source selection used for this job even if the user browsed meanwhile.
            self.data.update(times)
            self.data.update(selected=filename, playback=path, enabled=True, paused=False)
            self.data['request_id'] = uuid.uuid4().hex
            save(self.data)
            self.status.set_text('Iniciando el fondo…')
            request = self.data['request_id']
            GLib.timeout_add(500, self.check_renderer, request, time.monotonic() + 20)
        else:
            self.stream = Gtk.MediaFile.new_for_filename(path)
            self.stream.set_muted(True)
            self.stream.set_loop(True)
            self.stream.connect('notify::error', self.media_error)
            self.video.set_media_stream(self.stream)
            self.stream.play()
            self.status.set_text('Vista previa del fragmento con el fundido aplicado')
        return False

    def check_renderer(self, request, deadline):
        if self.data.get('request_id') != request or not self.data['enabled']:
            return False
        try:
            state = json.loads(config_path().with_name('status.json').read_text())
            if state.get('request_id') == request:
                if state.get('state') == 'error':
                    self.status.set_text('No se pudo aplicar el fondo: ' + state.get('message', 'Error del reproductor'))
                    return False
                if state.get('state') == 'playing':
                    self.status.set_text('Video iniciado como fondo. Puedes cerrar Luma.')
                    return False
        except (OSError, ValueError):
            pass
        if time.monotonic() > deadline:
            self.status.set_text('El fondo no confirmó el inicio. Comprueba Luma en la aplicación Extensiones; si acabas de instalar, cierra sesión y vuelve a entrar.')
            return False
        return True

    def pause(self, *_):
        self.data['paused'] = not self.data['paused']
        save(self.data)
        self.status.set_text('Pausa manual activada' if self.data['paused'] else 'Pausa manual desactivada; se mantienen las reglas de ahorro')

    def stop(self, *_):
        self.data['enabled'] = False
        save(self.data)
        self.status.set_text('Fondo detenido; se conserva el fondo estático del escritorio')

    def preview(self, *_):
        self.prepare_clip(False)

    def close(self, *_):
        if getattr(self, 'preparing', False):
            self.status.set_text('Espera a que termine la preparación antes de cerrar.')
            return True
        if self.stream:
            self.stream.pause()
        return False


def main():
    try:
        Gtk.init_check()
        if Gdk.Display.get_default() is None:
            print('Luma: no se pudo conectar al escritorio gráfico. Ejecuta desde una sesión GNOME Wayland.')
            return 1
        return Luma().run(None)
    except (ValueError, OSError) as e:
        print(f'Luma: {e}')
        return 1
