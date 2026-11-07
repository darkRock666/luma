"""Desktop setup, invoked by the application, never by the user in a terminal."""
import os
import time

EXTENSIONS_BUS = 'org.gnome.Shell.Extensions'


def ensure_extension():
    if os.environ.get('XDG_SESSION_TYPE') != 'wayland':
        raise RuntimeError('Luma requiere una sesión GNOME con Wayland. Elige esa sesión en la pantalla de inicio de sesión.')
    from gi.repository import Gio, GLib
    from .core import UUID
    proxy = Gio.DBusProxy.new_for_bus_sync(
        Gio.BusType.SESSION, Gio.DBusProxyFlags.NONE, None,
        EXTENSIONS_BUS, '/org/gnome/Shell/Extensions', EXTENSIONS_BUS, None)

    uuid = GLib.Variant('(s)', (UUID,))

    def call(method, args):
        try:
            return proxy.call_sync(method, args, Gio.DBusCallFlags.NONE, 5000, None).unpack()[0]
        except GLib.Error as error:
            raise RuntimeError('Luma no pudo comunicarse con el servicio de extensiones de GNOME. '
                               'Cierra sesión, vuelve a entrar en Ubuntu y abre Luma de nuevo.') from error

    info = call('GetExtensionInfo', uuid)
    if not info:
        raise RuntimeError('GNOME aún no reconoce la extensión instalada. Cierra sesión desde el menú del escritorio, vuelve a entrar y abre Luma. No necesitas usar la terminal.')
    state = info.get('state')
    if state == 4:
        raise RuntimeError('Esta versión de Luma requiere GNOME 50. La versión de tu escritorio no es compatible.')
    if state != 1:
        settings = Gio.Settings.new('org.gnome.shell')
        if settings.get_boolean('disable-user-extensions'):
            raise RuntimeError('Las extensiones están desactivadas en GNOME. Actívalas en la aplicación Extensiones y vuelve a elegir el video.')
        if call('EnableExtension', uuid):
            deadline = time.monotonic() + 5
            while True:
                info = call('GetExtensionInfo', uuid)
                state = info.get('state')
                if state == 1:
                    return
                # GNOME enables extensions asynchronously after the D-Bus reply.
                if state not in (2, 6, 8) or time.monotonic() >= deadline:
                    break
                time.sleep(0.1)
        detail = info.get('error', '')
        raise RuntimeError('GNOME no pudo activar Luma. ' + (detail or 'Cierra sesión, vuelve a entrar y abre Luma.'))
