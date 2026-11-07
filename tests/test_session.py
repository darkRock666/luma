import os
import sys
import types
import unittest
from unittest.mock import patch
from luma.session import ensure_extension

class SetupTests(unittest.TestCase):
    def setup_extension(self, infos, enabled=True):
        calls = []
        def call(method, *_):
            calls.append(method)
            value = enabled if method == 'EnableExtension' else infos.pop(0)
            return types.SimpleNamespace(unpack=lambda: (value,))
        def proxy(_bus, _flags, _info, name, path, interface, _cancel):
            self.assertEqual((name, path, interface), (
                'org.gnome.Shell.Extensions', '/org/gnome/Shell/Extensions',
                'org.gnome.Shell.Extensions'))
            return types.SimpleNamespace(call_sync=call)

        gio = types.SimpleNamespace(
            BusType=types.SimpleNamespace(SESSION=0),
            DBusProxyFlags=types.SimpleNamespace(NONE=0),
            DBusCallFlags=types.SimpleNamespace(NONE=0),
            DBusProxy=types.SimpleNamespace(new_for_bus_sync=proxy),
            Settings=types.SimpleNamespace(new=lambda *a: types.SimpleNamespace(get_boolean=lambda *a: False)))
        repo = types.ModuleType('gi.repository')
        repo.Gio = gio
        repo.GLib = types.SimpleNamespace(Variant=lambda *a: None)
        with patch.dict(os.environ, XDG_SESSION_TYPE='wayland'), patch.dict(sys.modules, {'gi.repository': repo}):
            ensure_extension()
        return calls

    def test_enable_and_verify(self):
        self.assertEqual(self.setup_extension([{'state': 2}, {'state': 8}, {'state': 1}]),
                         ['GetExtensionInfo', 'EnableExtension', 'GetExtensionInfo', 'GetExtensionInfo'])

    def test_already_active(self):
        self.assertEqual(self.setup_extension([{'state': 1}]), ['GetExtensionInfo'])

    def test_missing_extension(self):
        with self.assertRaisesRegex(RuntimeError, 'Cierra sesión'):
            self.setup_extension([{}])

    def test_activation_failure(self):
        with self.assertRaisesRegex(RuntimeError, 'no pudo activar'):
            self.setup_extension([{'state': 2}, {'state': 3}], False)

    def test_unsupported_shell(self):
        with self.assertRaisesRegex(RuntimeError, 'GNOME 50'):
            self.setup_extension([{'state': 4}])

    def test_x11_rejected(self):
        with patch.dict(os.environ, XDG_SESSION_TYPE='x11'):
            with self.assertRaisesRegex(RuntimeError, 'Wayland'):
                ensure_extension()
