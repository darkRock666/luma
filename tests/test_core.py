import json
import tempfile
import unittest
from pathlib import Path
from luma.core import load, save, validate_video


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / 'nested' / 'settings.json'

    def test_first_run_and_atomic_roundtrip(self):
        data = load(self.path)
        self.assertFalse(data['enabled'])
        data['videos'] = ['/tmp/á "video".mp4']
        save(data, self.path)
        self.assertEqual(load(self.path), data)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_reject_malformed_settings(self):
        self.path.parent.mkdir()
        for value in ({'paused': 'false'}, {'videos': [1]}, {'monitor': -1}, {'fit': 'bad'}, []):
            self.path.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                load(self.path)

    def test_video_validation_and_no_shell_interpretation(self):
        p = self.root / '$(touch nope); película.MP4'
        p.write_bytes(b'test')
        self.assertEqual(validate_video(p), str(p))
        self.assertFalse((self.root / 'nope').exists())
        with self.assertRaises(FileNotFoundError):
            validate_video(self.root / 'missing.mp4')
        with self.assertRaises(ValueError):
            validate_video(self.root)


if __name__ == '__main__':
    unittest.main()
