"""Infrastructure: recorder — WAV 16 kHz mono."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np

from infrastructure.recorder import RECORD_CHANNELS, RECORD_RATE, record_to_wav


def test_record_to_wav_accepts_duration_and_path():
    """Record for a short duration to a path; check file exists and format."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.wav"
        samples = int(0.1 * RECORD_RATE)
        fake_audio = np.zeros((samples, RECORD_CHANNELS), dtype=np.float32)
        with patch("infrastructure.recorder.sd.rec", return_value=fake_audio):
            with patch("infrastructure.recorder.sd.wait"):
                record_to_wav(path, duration_sec=0.1)
        assert path.exists()
        assert path.stat().st_size >= 44


def test_record_constants():
    assert RECORD_RATE == 16000
    assert RECORD_CHANNELS == 1
