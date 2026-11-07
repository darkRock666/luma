"""Luma persistence and input validation; no desktop dependencies."""
import json
import os
import tempfile
from pathlib import Path

VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mkv', '.mov', '.m4v', '.avi', '.ogv'}
DEFAULTS = dict(videos=[], selected='', enabled=False, paused=False,
                pause_fullscreen=True, pause_battery=True, fit='cover', monitor=0, playback='', trim_start=0.0, trim_end=0.0, crossfade=0.0, request_id='')
UUID = 'luma@local.desktop'


def config_path():
    return Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'luma' / 'settings.json'


def load(path=None):
    path = Path(path or config_path())
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        return dict(DEFAULTS, videos=[])
    if not isinstance(data, dict):
        raise ValueError('La configuración debe ser un objeto JSON.')
    result = dict(DEFAULTS, **{k: v for k, v in data.items() if k in DEFAULTS})
    for k in ('enabled', 'paused', 'pause_fullscreen', 'pause_battery'):
        if type(result[k]) is not bool:
            raise ValueError(f'Valor no válido: {k}')
    if not isinstance(result['videos'], list) or not all(isinstance(v, str) for v in result['videos']):
        raise ValueError('Biblioteca no válida.')
    if not isinstance(result['selected'], str) or result['fit'] not in ('cover', 'contain'):
        raise ValueError('Selección o ajuste no válido.')
    if type(result['monitor']) is not int or result['monitor'] < 0:
        raise ValueError('Monitor no válido.')
    import math
    for key in ('trim_start', 'trim_end', 'crossfade'):
        value = result[key]
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError(f'Tiempo no válido: {key}')
    if not isinstance(result['playback'], str):
        raise ValueError('Ruta de reproducción no válida.')
    return result


def save(data, path=None):
    path = Path(path or config_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.luma-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def validate_video(value):
    path = Path(value).expanduser().resolve(strict=True)
    if not path.is_file() or path.suffix.lower() not in VIDEO_EXTENSIONS:
        raise ValueError('Selecciona un video MP4, WebM, MKV, MOV, M4V, AVI u OGV.')
    if not os.access(path, os.R_OK):
        raise ValueError('No tienes permiso para leer este video.')
    return str(path)
