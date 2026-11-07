import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

// Only windows owned by our private Wayland client are ever adopted.
export default class Luma extends Extension {
    enable() {
        this._config = GLib.build_filenamev([GLib.get_user_config_dir(), 'luma', 'settings.json']);
        this._wallpaper = null;
        this._signature = '';
        this._paused = null;
        this._dead = false;
        this._windowSignal = global.window_manager.connect('map', (_wm, actor) => this._adopt(actor));
        this._monitorSignal = Main.layoutManager.connect('monitors-changed', () => {
            this._signature = '';
        });
        this._timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 1, () => {
            this._tick();
            return GLib.SOURCE_CONTINUE;
        });
        this._screenOff = false;
        this._screenSignal = Gio.DBus.session.signal_subscribe(
            'org.gnome.ScreenSaver', 'org.gnome.ScreenSaver', 'ActiveChanged',
            '/org/gnome/ScreenSaver', null, Gio.DBusSignalFlags.NONE,
            (_c, _s, _p, _i, _n, params) => { this._screenOff = params.deep_unpack()[0]; });
        this._power = null;
        Gio.DBusProxy.new_for_bus(Gio.BusType.SYSTEM, Gio.DBusProxyFlags.NONE, null,
            'org.freedesktop.UPower', '/org/freedesktop/UPower', 'org.freedesktop.UPower',
            null, (_source, result) => {
                try { if (!this._dead) this._power = Gio.DBusProxy.new_for_bus_finish(result); }
                catch (e) { console.warn(`Luma: UPower no disponible: ${e.message}`); }
            });
        this._tick();
    }

    _read() {
        try {
            const [ok, bytes] = GLib.file_get_contents(this._config);
            const value = ok ? JSON.parse(new TextDecoder().decode(bytes)) : {};
            return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
        } catch (_) { return {}; }
    }

    _tick() {
        const s = this._read();
        const monitor = Main.layoutManager.monitors[s.monitor ?? 0] ?? Main.layoutManager.primaryMonitor;
        const path = typeof s.playback === 'string' && s.playback ? s.playback :
            (typeof s.selected === 'string' ? s.selected : '');
        const valid = s.enabled === true && GLib.path_is_absolute(path) &&
            GLib.file_test(path, GLib.FileTest.IS_REGULAR) && monitor;
        const signature = valid ? JSON.stringify([path, s.fit, monitor, s.request_id]) : '';
        if (signature !== this._signature) {
            this._stop();
            this._signature = signature;
            if (valid) this._start(path, s.fit, monitor, s.request_id);
        }
        const onBattery = this._power?.get_cached_property('OnBattery')?.deep_unpack() === true;
        const fullscreen = monitor && global.display.get_monitor_in_fullscreen(monitor.index);
        const paused = s.paused === true || this._screenOff || Main.sessionMode.isLocked ||
            (s.pause_battery === true && onBattery) ||
            (s.pause_fullscreen === true && fullscreen);
        if (this._proc && this._ready && paused !== this._paused) {
            try { this._proc.send_signal(paused ? 10 : 12); this._paused = paused; }
            catch (e) { console.warn(`Luma: ${e.message}`); }
        }
    }

    _start(path, fit, monitor, request) {
        this._request = request;
        try {
            if (!global.context.get_wayland_compositor())
                throw new Error('Esta versión requiere GNOME con Wayland.');
            const player = GLib.build_filenamev([this.path, 'player.py']);
            const launcher = new Gio.SubprocessLauncher({flags: Gio.SubprocessFlags.NONE});
            launcher.setenv('GDK_BACKEND', 'wayland', true);
            this._client = Meta.WaylandClient.new_subprocess(global.context, launcher,
                ['/usr/bin/python3', player, path, fit === 'contain' ? 'contain' : 'cover', request ?? '']);
            this._proc = this._client.get_subprocess();
            this._geometry = monitor;
            // Do not send user signals before Python installs its handlers.
            this._paused = null;
            this._ready = false;
            const proc = this._proc;
            proc.wait_async(null, (p, result) => {
                try { p.wait_finish(result); } catch (_) {}
                if (!this._dead && this._proc === proc) {
                    this._stop();
                    this._status('error', 'El reproductor se detuvo. Prueba otro video o vuelve a aplicar.');
                }
            });
        } catch (e) { this._status('error', e.message); }
    }

    _status(state, message) {
        try {
            GLib.file_set_contents(GLib.build_filenamev([GLib.get_user_config_dir(), 'luma', 'status.json']),
                JSON.stringify({request_id: this._request, state, message}));
        } catch (e) { console.warn(`Luma: ${e.message}`); }
    }

    _adopt(actor) {
        const win = actor.meta_window;
        if (this._wallpaper || !win || !this._client?.owns_window(win)) return;
        try {
            win.stick();
            const m = this._geometry;
            win.move_resize_frame(false, m.x, m.y, m.width, m.height);
            // Let Mutter keep the source window and paint its live clone as wallpaper.
            this._wallpaper = new Clutter.Clone({
                source: actor, reactive: false,
                x: m.x, y: m.y, width: m.width, height: m.height,
            });
            Main.layoutManager._backgroundGroup.add_child(this._wallpaper);
            // Mutter disallows minimizing windows excluded from the taskbar.
            win.minimize();
            if (!win.minimized)
                throw new Error('No se pudo minimizar la ventana del reproductor.');
            win.hide_from_window_list();
            this._ready = true;
        } catch (e) {
            this._stop();
            this._status('error', 'GNOME no pudo colocar el video en el escritorio. ' + e.message);
        }
    }

    _stop() {
        this._wallpaper?.destroy();
        this._wallpaper = null;
        if (this._proc) {
            try { this._proc.force_exit(); } catch (_) {}
        }
        this._proc = null;
        this._client = null;
        this._paused = null;
    }

    disable() {
        this._dead = true;
        if (this._timer) GLib.source_remove(this._timer);
        global.window_manager.disconnect(this._windowSignal);
        Main.layoutManager.disconnect(this._monitorSignal);
        Gio.DBus.session.signal_unsubscribe(this._screenSignal);
        this._stop();
        this._power = null;
    }
}
