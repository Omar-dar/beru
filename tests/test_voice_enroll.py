import os
import tempfile
import unittest

import numpy as np
import soundfile as sf

from src.audio_util import load_mono_16k
from src.voice_auth import enroll_audio_paths


class AudioUtilTests(unittest.TestCase):
    def _write_wav(self, seconds=2.0, amplitude=0.3):
        sr = 16000
        t = np.linspace(0, seconds, int(sr * seconds), endpoint=False)
        y = (amplitude * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
        f = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        sf.write(f.name, y, sr)
        return f.name

    def test_enroll_wav(self):
        path = self._write_wav()
        try:
            result = enroll_audio_paths([path])
            self.assertTrue(result['ok'], result)
        finally:
            os.unlink(path)

    def test_reject_silent_clip(self):
        path = self._write_wav(amplitude=0.0)
        try:
            y, err = load_mono_16k(path)
            self.assertIsNone(y)
            self.assertIn('quiet', (err or '').lower())
        finally:
            os.unlink(path)


if __name__ == '__main__':
    unittest.main()
