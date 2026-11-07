"""Private GTK renderer, owned by Mutter through Meta.WaylandClient."""
import json
import os
from pathlib import Path
import signal
import sys
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio, GLib, GLibUnix


class Renderer(Gtk.Application):
    def __init__(self, filename, fit):
        super().__init__(application_id='local.luma.Renderer', flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.filename, self.fit = filename, fit
        self.connect('activate', self.activate_window)

    def activate_window(self, *_):
        self.adopted = False
        self.requested_playing = True
        self.frames = 0
        self.last_position = None
        self.last_progress_us = GLib.get_monotonic_time()
        self.stream = Gtk.MediaFile.new_for_filename(self.filename)
        self.stream.set_loop(True)
        self.stream.set_muted(True)
        self.stream.connect('notify::error', self.on_error)
        self.stream.connect('notify::prepared', self.on_prepared)
        self.stream.connect('invalidate-contents', self.on_frame)
        self.video = Gtk.Picture.new_for_paintable(self.stream)
        self.video.set_can_shrink(True)
        if hasattr(self.video, 'set_content_fit'):
            self.video.set_content_fit(Gtk.ContentFit.COVER if self.fit == 'cover' else Gtk.ContentFit.CONTAIN)
        win = Gtk.ApplicationWindow(application=self, title='Luma renderer')
        win.set_decorated(False)
        win.set_default_size(960, 540)
        win.set_child(self.video)
        GLibUnix.signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, self.set_playing, False)
        GLibUnix.signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR2, self.set_playing, True)
        win.present()
        self.stream.play()
        GLib.timeout_add_seconds(2, self.sample_playback)

    def set_playing(self, value):
        self.requested_playing = value
        self.last_progress_us = GLib.get_monotonic_time()
        self.stream.set_playing(value)
        # GNOME only sends playback controls after placing the window on the desktop.
        if not self.adopted:
            self.adopted = True
            self.on_prepared()
        return GLib.SOURCE_CONTINUE

    def on_frame(self, *_):
        self.frames += 1

    def sample_playback(self):
        now = GLib.get_monotonic_time()
        position = self.stream.get_timestamp()
        if position != self.last_position:
            self.last_position = position
            self.last_progress_us = now
        duration = self.stream.get_duration()
        stuck_at_end = (duration > 0 and position >= duration - 250_000
                        and now - self.last_progress_us >= 1_500_000)
        # GTK can stay in the playing state at EOF without restarting its loop.
        if (self.requested_playing and self.stream.is_seekable()
                and (self.stream.get_ended() or stuck_at_end)):
            self.stream.seek(0)
            self.stream.play()
            self.last_progress_us = now
        self.write_status('playback-diagnostics.json', {
            'monotonic_us': now,
            'requested_playing': self.requested_playing,
            'playing': self.stream.get_playing(),
            'position_us': position,
            'ended': self.stream.get_ended(),
            'frames': self.frames,
        })
        return GLib.SOURCE_CONTINUE

    def write_status(self, filename, data):
        directory = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'luma'
        try:
            directory.mkdir(parents=True, exist_ok=True)
            temp = directory / f'.{filename}-{os.getpid()}'
            data['request_id'] = sys.argv[3] if len(sys.argv) > 3 else ''
            temp.write_text(json.dumps(data))
            temp.replace(directory / filename)
        except OSError:
            pass

    def report(self, state, message=''):
        self.write_status('status.json', dict(state=state, message=message))

    def on_prepared(self, *_):
        if self.adopted and self.stream.is_prepared() and not self.stream.get_error():
            self.report('playing')

    def on_error(self, *_):
        if self.stream.get_error():
            self.report('error', self.stream.get_error().message)
            print(self.stream.get_error().message, file=sys.stderr, flush=True)
            self.quit()


if __name__ == '__main__':
    Renderer(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'cover').run([])
