import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from luma.loop import prepare


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'Requiere FFmpeg y ffprobe')
class EncodingTests(unittest.TestCase):
    def test_real_trim_crossfade_and_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'source.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                            'testsrc2=size=160x90:rate=30:duration=5', '-c:v', 'libx264', str(source)], check=True)
            result = prepare(str(source), .5, 4.5, .5, Path(tmp) / 'cache')
            probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                    '-of', 'json', result], capture_output=True, text=True, check=True)
            self.assertAlmostEqual(float(json.loads(probe.stdout)['format']['duration']), 3.5, delta=.1)
            before = Path(result).stat().st_mtime_ns
            self.assertEqual(prepare(str(source), .5, 4.5, .5, Path(tmp) / 'cache'), result)
            self.assertEqual(Path(result).stat().st_mtime_ns, before)
