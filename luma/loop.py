"""Prepare one cached seamless clip, avoiding two decoders during playback."""
import hashlib
import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def bounds(start, end, fade, duration):
    values = (start, end, fade, duration)
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in values):
        raise ValueError('Los tiempos deben ser números finitos.')
    end = duration if end == 0 else end
    if start < 0 or end > duration + .001 or end - start < .2:
        raise ValueError('La salida debe estar después de la entrada y dentro del video (mínimo 0,2 s).')
    if fade < 0 or fade > 10 or fade * 2 >= end - start:
        raise ValueError('La transición debe durar menos de la mitad del fragmento y como máximo 10 s.')
    return start, end, fade


def filter_graph(length, fade):
    base = 'fps=30,scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1,format=yuv420p,settb=AVTB,setpts=PTS-STARTPTS'
    if fade == 0:
        return f'[0:v]{base}[out]'
    # Start at t=fade. Finish with tail->head, ending at source t=fade.
    # Therefore the file boundary continues the source motion rather than cutting back to t=0.
    return (f'[0:v]{base},split=3[m][t][h];'
            f'[m]trim=start={fade}:end={length-fade},setpts=PTS-STARTPTS[mid];'
            f'[t]trim=start={length-fade}:end={length},setpts=PTS-STARTPTS[tail];'
            f'[h]trim=end={fade},setpts=PTS-STARTPTS[head];'
            f'[tail][head]xfade=transition=fade:duration={fade}:offset=0,trim=duration={fade},setpts=PTS-STARTPTS[blend];'
            '[mid][blend]concat=n=2:v=1:a=0,format=yuv420p[out]')


def prepare(filename, start=0, end=0, fade=1, cache=None):
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        raise ValueError('Falta FFmpeg. Instala el paquete ffmpeg para preparar el bucle.')
    probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                            '-show_entries', 'stream=duration:format=duration', '-of', 'json', filename],
                           capture_output=True, text=True, timeout=30)
    if probe.returncode:
        raise ValueError('No se pudo leer el video: ' + probe.stderr[-500:])
    info = json.loads(probe.stdout)
    if not info.get('streams'):
        raise ValueError('El archivo no contiene video.')
    raw_duration = info['streams'][0].get('duration', 'N/A')
    if raw_duration == 'N/A':
        raw_duration = info.get('format', {}).get('duration', 0)
    start, end, fade = bounds(start, end, fade, float(raw_duration))
    stat = Path(filename).stat()
    key = hashlib.sha256(json.dumps([str(Path(filename).resolve()), stat.st_size, stat.st_mtime_ns,
                                    start, end, fade, 'luma-loop-v1']).encode()).hexdigest()
    cache = Path(cache or Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')) / 'luma')
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / f'{key}.mp4'
    if target.is_file() and target.stat().st_size:
        return str(target)
    fd, temp = tempfile.mkstemp(suffix='.mp4', prefix='.preparing-', dir=cache)
    os.close(fd)
    try:
        result = subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
            '-ss', str(start), '-t', str(end-start), '-i', filename,
            '-filter_complex_threads', '1', '-filter_complex', filter_graph(end-start, fade),
            '-map', '[out]', '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
            '-pix_fmt', 'yuv420p', '-movflags', '+faststart', temp], capture_output=True, text=True)
        if result.returncode:
            raise ValueError('No se pudo preparar el bucle: ' + result.stderr[-1200:])
        os.replace(temp, target)
        return str(target)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
