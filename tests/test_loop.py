import unittest
from unittest.mock import patch
from luma.loop import bounds, filter_graph, prepare


class LoopTests(unittest.TestCase):
    def test_end_defaults_to_duration(self):
        self.assertEqual(bounds(2, 0, 1, 12), (2, 12, 1))

    def test_reject_bad_ranges(self):
        for values in [(5, 2, 1, 10), (-1, 3, 1, 10), (0, 11, 1, 10),
                       (0, 2, 1, 10), (0, 4, -1, 10), (0, 10, float('nan'), 10)]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                bounds(*values)

    def test_missing_ffmpeg_is_actionable(self):
        with patch('luma.loop.shutil.which', return_value=None):
            with self.assertRaisesRegex(ValueError, 'Falta FFmpeg'):
                prepare('/video.mp4')

    def test_filter_continuous_file_boundary(self):
        graph = filter_graph(10, 1)
        self.assertIn('trim=start=1:end=9', graph)
        self.assertIn('trim=start=9:end=10', graph)
        self.assertIn('xfade=transition=fade:duration=1:offset=0', graph)
        self.assertNotIn('xfade', filter_graph(10, 0))
