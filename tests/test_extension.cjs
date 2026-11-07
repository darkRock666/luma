// Exercise the extension's lifecycle without a running GNOME Shell.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
let source = fs.readFileSync('extension/extension.js', 'utf8')
    .replace(/^import .*;\n/gm, '').replace('export default class Luma', 'globalThis.Luma = class Luma');
const monitor = {index: 0, x: 0, y: 0, width: 1920, height: 1080};
const context = {Extension: class {}, TextDecoder, console, Gio: {}, GLib: {
    path_is_absolute: s => s.startsWith('/'), file_test: () => true, FileTest: {IS_REGULAR: 1}},
    Main: {layoutManager: {monitors: [monitor], primaryMonitor: monitor}, sessionMode: {isLocked: false}},
    global: {display: {get_monitor_in_fullscreen: () => false}}};
vm.createContext(context);
vm.runInContext(source, context);
const luma = new context.Luma();
let starts = 0, stops = 0;
const signals = [];
luma._signature = '';
luma._read = () => ({enabled: true, selected: '/movie.mp4', pause_fullscreen: true, pause_battery: true});
luma._stop = () => { stops++; luma._proc = null; };
luma._start = () => { starts++; luma._ready = false; luma._proc = {send_signal: n => signals.push(n)}; };
luma._tick();
assert.equal(starts, 1);
assert.deepEqual(signals, [], 'No signals may be sent before the renderer is ready');
luma._ready = true;
luma._paused = null;
luma._tick();
assert.deepEqual(signals, [12]);
context.global.display.get_monitor_in_fullscreen = () => true;
luma._tick();
assert.deepEqual(signals, [12, 10]);
luma._tick();
assert.equal(signals.length, 2, 'Repeated polling must not send redundant signals');
context.global.display.get_monitor_in_fullscreen = () => false;
luma._power = {get_cached_property: () => ({deep_unpack: () => true})};
luma._tick();
assert.equal(signals.length, 2, 'Battery keeps playback paused after fullscreen closes');
luma._power = null;
luma._tick();
assert.deepEqual(signals, [12, 10, 12]);
luma._read = () => ({enabled: false});
luma._tick();
assert.equal(luma._proc, null);
assert.equal(starts, 1);
assert.equal(stops, 2);

class Actor {
    children = [];
    parent = null;
    get_parent() { return this.parent; }
    add_child(actor) { this.children.push(actor); actor.parent = this; }
    remove_child(actor) { this.children.splice(this.children.indexOf(actor), 1); actor.parent = null; }
    set_child_below_sibling(actor) { this.remove_child(actor); this.children.unshift(actor); actor.parent = this; }
    destroy() { this.parent?.remove_child(this); }
}
context.Clutter = {Clone: class extends Actor {
    constructor(properties) { super(); Object.assign(this, properties); }
}};
const windowGroup = new Actor();
const backgroundGroup = new Actor();
const staticWallpaper = new Actor();
backgroundGroup.add_child(staticWallpaper);
context.Main.layoutManager._backgroundGroup = backgroundGroup;
const renderer = new Actor();
renderer.meta_window = {
    hide_from_window_list() { this.skipTaskbar = true; },
    stick() {}, move_resize_frame() {},
    minimize() { if (!this.skipTaskbar) this.minimized = true; },
};
windowGroup.add_child(renderer);
const wallpaper = new context.Luma();
wallpaper._geometry = monitor;
wallpaper._client = {owns_window: window => window === renderer.meta_window};
wallpaper._adopt(renderer);
assert.equal(wallpaper._ready, true);
assert.equal(renderer.get_parent(), windowGroup);
assert.equal(renderer.meta_window.minimized, true);
assert.equal(renderer.meta_window.skipTaskbar, true);
// Mutter lowers the renderer inside its current parent when focus changes.
renderer.get_parent().set_child_below_sibling(renderer, null);
assert.equal(backgroundGroup.children[0], staticWallpaper);
assert.equal(backgroundGroup.children[1].source, renderer);
assert.equal(backgroundGroup.children[1].reactive, false);
wallpaper._stop();
assert.deepEqual(backgroundGroup.children, [staticWallpaper]);
assert.equal(renderer.get_parent(), windowGroup);
console.log('Extension policy/lifecycle checks passed');
